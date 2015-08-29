from __future__ import absolute_import
import Cookie
import copy
import threading
import time
import urllib
import urlparse
from email.utils import parsedate_tz, formatdate, mktime_tz

import netlib
from netlib import http, tcp, odict, utils, encoding
from netlib.http import cookies, http1, http2
from netlib.http.http1 import HTTP1Protocol
from netlib.http.semantics import CONTENT_MISSING

from .tcp import TCPHandler
from .primitives import KILL, ProtocolHandler, Flow, Error
from ..proxy.connection import ServerConnection
from .. import utils, controller, stateobject, proxy

from .http_wrappers import decoded, HTTPRequest, HTTPResponse


class KillSignal(Exception):
    pass


def send_connect_request(conn, host, port, update_state=True):
    upstream_request = HTTPRequest(
        "authority",
        "CONNECT",
        None,
        host,
        port,
        None,
        (1, 1),
        odict.ODictCaseless(),
        ""
    )

    # we currently only support HTTP/1 CONNECT requests
    protocol = http1.HTTP1Protocol(conn)

    conn.send(protocol.assemble(upstream_request))
    resp = HTTPResponse.from_protocol(protocol, upstream_request.method)
    if resp.status_code != 200:
        raise proxy.ProxyError(resp.status_code,
                               "Cannot establish SSL " +
                               "connection with upstream proxy: \r\n" +
                               repr(resp))
    if update_state:
        conn.state.append(("http", {
            "state": "connect",
            "host": host,
            "port": port}
        ))
    return resp


class HTTPFlow(Flow):
    """
    A HTTPFlow is a collection of objects representing a single HTTP
    transaction. The main attributes are:

        request: HTTPRequest object
        response: HTTPResponse object
        error: Error object
        server_conn: ServerConnection object
        client_conn: ClientConnection object

    Note that it's possible for a Flow to have both a response and an error
    object. This might happen, for instance, when a response was received
    from the server, but there was an error sending it back to the client.

    The following additional attributes are exposed:

        intercepted: Is this flow currently being intercepted?
        live: Does this flow have a live client connection?
    """

    def __init__(self, client_conn, server_conn, live=None):
        super(HTTPFlow, self).__init__("http", client_conn, server_conn, live)
        self.request = None
        """@type: HTTPRequest"""
        self.response = None
        """@type: HTTPResponse"""

    _stateobject_attributes = Flow._stateobject_attributes.copy()
    _stateobject_attributes.update(
        request=HTTPRequest,
        response=HTTPResponse
    )

    @classmethod
    def from_state(cls, state):
        f = cls(None, None)
        f.load_state(state)
        return f

    def __repr__(self):
        s = "<HTTPFlow"
        for a in ("request", "response", "error", "client_conn", "server_conn"):
            if getattr(self, a, False):
                s += "\r\n  %s = {flow.%s}" % (a, a)
        s += ">"
        return s.format(flow=self)

    def copy(self):
        f = super(HTTPFlow, self).copy()
        if self.request:
            f.request = self.request.copy()
        if self.response:
            f.response = self.response.copy()
        return f

    def match(self, f):
        """
            Match this flow against a compiled filter expression. Returns True
            if matched, False if not.

            If f is a string, it will be compiled as a filter expression. If
            the expression is invalid, ValueError is raised.
        """
        if isinstance(f, basestring):
            from .. import filt

            f = filt.parse(f)
            if not f:
                raise ValueError("Invalid filter expression.")
        if f:
            return f(self)
        return True

    def replace(self, pattern, repl, *args, **kwargs):
        """
            Replaces a regular expression pattern with repl in both request and
            response of the flow. Encoded content will be decoded before
            replacement, and re-encoded afterwards.

            Returns the number of replacements made.
        """
        c = self.request.replace(pattern, repl, *args, **kwargs)
        if self.response:
            c += self.response.replace(pattern, repl, *args, **kwargs)
        return c


class HTTPHandler(ProtocolHandler):
    """
    HTTPHandler implements mitmproxys understanding of the HTTP protocol.

    """

    def __init__(self, c):
        super(HTTPHandler, self).__init__(c)
        self.expected_form_in = c.config.mode.http_form_in
        self.expected_form_out = c.config.mode.http_form_out
        self.skip_authentication = False

    def handle_messages(self):
        while self.handle_flow():
            pass

    def get_response_from_server(self, flow):
        self.c.establish_server_connection()

        for attempt in (0, 1):
            try:
                if not self.c.server_conn.protocol:
                    # instantiate new protocol if connection does not have one yet
                    # TODO: select correct protocol based on ALPN (?)
                    self.c.server_conn.protocol = http1.HTTP1Protocol(self.c.server_conn)
                    # self.c.server_conn.protocol = http2.HTTP2Protocol(self.c.server_conn)
                    # self.c.server_conn.protocol.perform_connection_preface()

                self.c.server_conn.send(self.c.server_conn.protocol.assemble(flow.request))

                # Only get the headers at first...
                flow.response = HTTPResponse.from_protocol(
                    self.c.server_conn.protocol,
                    flow.request.method,
                    body_size_limit=self.c.config.body_size_limit,
                    include_body=False,
                )
                break
            except (tcp.NetLibError, http.HttpErrorConnClosed) as v:
                self.c.log(
                    "error in server communication: %s" % repr(v),
                    level="debug"
                )
                if attempt == 0:
                    # In any case, we try to reconnect at least once. This is
                    # necessary because it might be possible that we already
                    # initiated an upstream connection after clientconnect that
                    # has already been expired, e.g consider the following event
                    # log:
                    # > clientconnect (transparent mode destination known)
                    # > serverconnect
                    # > read n% of large request
                    # > server detects timeout, disconnects
                    # > read (100-n)% of large request
                    # > send large request upstream
                    self.c.server_reconnect()
                else:
                    raise

        # call the appropriate script hook - this is an opportunity for an
        # inline script to set flow.stream = True
        flow = self.c.channel.ask("responseheaders", flow)
        if flow is None or flow == KILL:
            raise KillSignal()
        else:
            # now get the rest of the request body, if body still needs to be
            # read but not streaming this response
            if flow.response.stream:
                flow.response.content = CONTENT_MISSING
            else:
                if isinstance(self.c.server_conn.protocol, http1.HTTP1Protocol):
                    # streaming is only supported with HTTP/1 at the moment
                    flow.response.content = self.c.server_conn.protocol.read_http_body(
                        flow.response.headers,
                        self.c.config.body_size_limit,
                        flow.request.method,
                        flow.response.code,
                        False
                    )
        flow.response.timestamp_end = utils.timestamp()

    def handle_flow(self):
        flow = HTTPFlow(self.c.client_conn, self.c.server_conn, self.live)

        try:
            try:
                if not flow.client_conn.protocol:
                    # instantiate new protocol if connection does not have one yet
                    # the first request might be a CONNECT - which is currently only supported with HTTP/1
                    flow.client_conn.protocol = http1.HTTP1Protocol(self.c.client_conn)

                req = HTTPRequest.from_protocol(
                    flow.client_conn.protocol,
                    body_size_limit=self.c.config.body_size_limit
                )
            except tcp.NetLibError:
                # don't throw an error for disconnects that happen
                # before/between requests.
                return False

            self.c.log(
                "request",
                "debug",
                [repr(req)]
            )
            ret = self.process_request(flow, req)
            if ret:
                # instantiate new protocol if connection does not have one yet
                # TODO: select correct protocol based on ALPN (?)
                flow.client_conn.protocol = http1.HTTP1Protocol(self.c.client_conn)
                # flow.client_conn.protocol = http2.HTTP2Protocol(self.c.client_conn, is_server=True)
            if ret is not None:
                return ret

            # Be careful NOT to assign the request to the flow before
            # process_request completes. This is because the call can raise an
            # exception. If the request object is already attached, this results
            # in an Error object that has an attached request that has not been
            # sent through to the Master.
            flow.request = req
            request_reply = self.c.channel.ask("request", flow)
            if request_reply is None or request_reply == KILL:
                raise KillSignal()

            # The inline script may have changed request.host
            self.process_server_address(flow)

            if isinstance(request_reply, HTTPResponse):
                flow.response = request_reply
            else:
                self.get_response_from_server(flow)

            # no further manipulation of self.c.server_conn beyond this point
            # we can safely set it as the final attribute value here.
            flow.server_conn = self.c.server_conn

            self.c.log(
                "response",
                "debug",
                [repr(flow.response)]
            )
            response_reply = self.c.channel.ask("response", flow)
            if response_reply is None or response_reply == KILL:
                raise KillSignal()

            self.send_response_to_client(flow)

            if self.check_close_connection(flow):
                return False

            # We sent a CONNECT request to an upstream proxy.
            if flow.request.form_in == "authority" and flow.response.code == 200:
                # TODO: Possibly add headers (memory consumption/usefulness
                # tradeoff) Make sure to add state info before the actual
                # processing of the CONNECT request happens. During an SSL
                # upgrade, we may receive an SNI indication from the client,
                # which resets the upstream connection. If this is the case, we
                # must already re-issue the CONNECT request at this point.
                self.c.server_conn.state.append(
                    (
                        "http", {
                            "state": "connect",
                            "host": flow.request.host,
                            "port": flow.request.port
                        }
                    )
                )
                if not self.process_connect_request(
                        (flow.request.host, flow.request.port)):
                    return False

            # If the user has changed the target server on this connection,
            # restore the original target server
            flow.live.restore_server()

            return True  # Next flow please.
        except (
                http.HttpAuthenticationError,
                http.HttpError,
                proxy.ProxyError,
                tcp.NetLibError,
        ) as e:
            self.handle_error(e, flow)
        except KillSignal:
            self.c.log("Connection killed", "info")
        finally:
            flow.live = None  # Connection is not live anymore.
        return False

    def handle_server_reconnect(self, state):
        if state["state"] == "connect":
            send_connect_request(
                self.c.server_conn,
                state["host"],
                state["port"],
                update_state=False
            )
        else:  # pragma: nocover
            raise RuntimeError("Unknown State: %s" % state["state"])

    def handle_error(self, error, flow=None):
        message = repr(error)
        message_debug = None

        if isinstance(error, tcp.NetLibError):
            message = None
            message_debug = "TCP connection closed unexpectedly."
        elif "tlsv1 alert unknown ca" in message:
            message = "TLSv1 Alert Unknown CA: The client does not trust the proxy's certificate."
        elif "handshake error" in message:
            message_debug = message
            message = "SSL handshake error: The client may not trust the proxy's certificate."

        if message:
            self.c.log(message, level="info")
        if message_debug:
            self.c.log(message_debug, level="debug")

        if flow:
            # TODO: no flows without request or with both request and response
            # at the moment.
            if flow.request and not flow.response:
                flow.error = Error(message or message_debug)
                self.c.channel.ask("error", flow)
        try:
            status_code = getattr(error, "code", 502)
            headers = getattr(error, "headers", None)

            html_message = message or ""
            if message_debug:
                html_message += "<pre>%s</pre>" % message_debug
            self.send_error(status_code, html_message, headers)
        except:
            pass

    def send_error(self, status_code, message, headers):
        response = http.status_codes.RESPONSES.get(status_code, "Unknown")
        body = """
            <html>
                <head>
                    <title>%d %s</title>
                </head>
                <body>%s</body>
            </html>
        """ % (status_code, response, message)

        if not headers:
            headers = odict.ODictCaseless()
        assert isinstance(headers, odict.ODictCaseless)

        headers["Server"] = [self.c.config.server_version]
        headers["Connection"] = ["close"]
        headers["Content-Length"] = [len(body)]
        headers["Content-Type"] = ["text/html"]

        resp = HTTPResponse(
            (1, 1),  # if HTTP/2 is used, this value is ignored anyway
            status_code,
            response,
            headers,
            body,
        )

        # if no protocol is assigned yet - just assume HTTP/1
        # TODO: maybe check ALPN and use HTTP/2 if required?
        protocol = self.c.client_conn.protocol or http1.HTTP1Protocol(self.c.client_conn)
        self.c.client_conn.send(protocol.assemble(resp))

    def process_request(self, flow, request):
        """
        @returns:
        True, if the request should not be sent upstream
        False, if the connection should be aborted
        None, if the request should be sent upstream
        (a status code != None should be returned directly by handle_flow)
        """

        if not self.skip_authentication:
            self.authenticate(request)

        # Determine .scheme, .host and .port attributes
        # For absolute-form requests, they are directly given in the request.
        # For authority-form requests, we only need to determine the request scheme.
        # For relative-form requests, we need to determine host and port as
        # well.
        if not request.scheme:
            request.scheme = "https" if flow.server_conn and flow.server_conn.ssl_established else "http"
        if not request.host:
            # Host/Port Complication: In upstream mode, use the server we CONNECTed to,
            # not the upstream proxy.
            if flow.server_conn:
                for s in flow.server_conn.state:
                    if s[0] == "http" and s[1]["state"] == "connect":
                        request.host, request.port = s[1]["host"], s[1]["port"]
            if not request.host and flow.server_conn:
                request.host, request.port = flow.server_conn.address.host, flow.server_conn.address.port


        # Now we can process the request.
        if request.form_in == "authority":
            if self.c.client_conn.ssl_established:
                raise http.HttpError(
                    400,
                    "Must not CONNECT on already encrypted connection"
                )

            if self.c.config.mode == "regular":
                self.c.set_server_address((request.host, request.port))
                # Update server_conn attribute on the flow
                flow.server_conn = self.c.server_conn

                # since we currently only support HTTP/1 CONNECT requests
                # the response must be HTTP/1 as well
                self.c.client_conn.send(
                    ('HTTP/%s.%s 200 ' % (request.httpversion[0], request.httpversion[1])) +
                    'Connection established\r\n' +
                    'Content-Length: 0\r\n' +
                    ('Proxy-agent: %s\r\n' % self.c.config.server_version) +
                    '\r\n'
                )
                return self.process_connect_request(self.c.server_conn.address)
            elif self.c.config.mode == "upstream":
                return None
            else:
                # CONNECT should never occur if we don't expect absolute-form
                # requests
                pass

        elif request.form_in == self.expected_form_in:
            request.form_out = self.expected_form_out
            if request.form_in == "absolute":
                if request.scheme != "http":
                    raise http.HttpError(
                        400,
                        "Invalid request scheme: %s" % request.scheme
                    )
                if self.c.config.mode == "regular":
                    # Update info so that an inline script sees the correct
                    # value at flow.server_conn
                    self.c.set_server_address((request.host, request.port))
                    flow.server_conn = self.c.server_conn

            elif request.form_in == "relative":
                if self.c.config.mode == "spoof":
                    # Host header
                    h = request.pretty_host(hostheader=True)
                    if h is None:
                        raise http.HttpError(
                            400,
                            "Invalid request: No host information"
                        )
                    p = netlib.utils.parse_url("http://" + h)
                    request.scheme = p[0]
                    request.host = p[1]
                    request.port = p[2]
                    self.c.set_server_address((request.host, request.port))
                    flow.server_conn = self.c.server_conn

                if self.c.config.mode == "sslspoof":
                    # SNI is processed in server.py
                    if not (flow.server_conn and flow.server_conn.ssl_established):
                        raise http.HttpError(
                            400,
                            "Invalid request: No host information"
                        )

            return None

        raise http.HttpError(
            400, "Invalid HTTP request form (expected: %s, got: %s)" % (
                self.expected_form_in, request.form_in
            )
        )

    def process_server_address(self, flow):
        # Depending on the proxy mode, server handling is entirely different
        # We provide a mostly unified API to the user, which needs to be
        # unfiddled here
        # ( See also: https://github.com/mitmproxy/mitmproxy/issues/337 )
        address = tcp.Address((flow.request.host, flow.request.port))

        ssl = (flow.request.scheme == "https")

        if self.c.config.mode == "upstream":
            # The connection to the upstream proxy may have a state we may need
            # to take into account.
            connected_to = None
            for s in flow.server_conn.state:
                if s[0] == "http" and s[1]["state"] == "connect":
                    connected_to = tcp.Address((s[1]["host"], s[1]["port"]))

            # We need to reconnect if the current flow either requires a
            # (possibly impossible) change to the connection state, e.g. the
            # host has changed but we already CONNECTed somewhere else.
            needs_server_change = (
                ssl != self.c.server_conn.ssl_established
                or
                # HTTP proxying is "stateless", CONNECT isn't.
                (connected_to and address != connected_to)
            )

            if needs_server_change:
                # force create new connection to the proxy server to reset
                # state
                self.live.change_server(self.c.server_conn.address, force=True)
                if ssl:
                    send_connect_request(
                        self.c.server_conn,
                        address.host,
                        address.port
                    )
                    self.c.establish_ssl(server=True)
        else:
            # If we're not in upstream mode, we just want to update the host
            # and possibly establish TLS. This is a no op if the addresses
            # match.
            self.live.change_server(address, ssl=ssl)

        flow.server_conn = self.c.server_conn

    def send_response_to_client(self, flow):
        if not flow.response.stream:
            # no streaming:
            # we already received the full response from the server and can
            # send it to the client straight away.
            self.c.client_conn.send(self.c.client_conn.protocol.assemble(flow.response))
        else:
            if isinstance(self.c.client_conn.protocol, http2.HTTP2Protocol):
                raise NotImplementedError("HTTP streaming with HTTP/2 is currently not supported.")


            # streaming:
            # First send the headers and then transfer the response
            # incrementally:
            h = self.c.client_conn.protocol._assemble_response_first_line(flow.response)
            self.c.client_conn.send(h + "\r\n")
            h = self.c.client_conn.protocol._assemble_response_headers(flow.response, preserve_transfer_encoding=True)
            self.c.client_conn.send(h + "\r\n")

            chunks = self.c.server_conn.protocol.read_http_body_chunked(
                flow.response.headers,
                self.c.config.body_size_limit,
                flow.request.method,
                flow.response.code,
                False,
                4096
            )

            if callable(flow.response.stream):
                chunks = flow.response.stream(chunks)

            for chunk in chunks:
                for part in chunk:
                    self.c.client_conn.wfile.write(part)
                self.c.client_conn.wfile.flush()

            flow.response.timestamp_end = utils.timestamp()

    def check_close_connection(self, flow):
        """
            Checks if the connection should be closed depending on the HTTP
            semantics. Returns True, if so.
        """

        # TODO: add logic for HTTP/2

        close_connection = (
            http1.HTTP1Protocol.connection_close(
                flow.request.httpversion,
                flow.request.headers
            ) or http1.HTTP1Protocol.connection_close(
                flow.response.httpversion,
                flow.response.headers
            ) or http1.HTTP1Protocol.expected_http_body_size(
                flow.response.headers,
                False,
                flow.request.method,
                flow.response.code) == -1
            )
        if close_connection:
            if flow.request.form_in == "authority" and flow.response.code == 200:
                # Workaround for
                # https://github.com/mitmproxy/mitmproxy/issues/313: Some
                # proxies (e.g. Charles) send a CONNECT response with HTTP/1.0
                # and no Content-Length header
                pass
            else:
                return True
        return False

    def process_connect_request(self, address):
        """
        Process a CONNECT request.
        Returns True if the CONNECT request has been processed successfully.
        Returns False, if the connection should be closed immediately.
        """
        address = tcp.Address.wrap(address)
        if self.c.config.check_ignore(address):
            self.c.log("Ignore host: %s:%s" % address(), "info")
            TCPHandler(self.c, log=False).handle_messages()
            return False
        else:
            self.expected_form_in = "relative"
            self.expected_form_out = "relative"
            self.skip_authentication = True

            # In practice, nobody issues a CONNECT request to send unencrypted
            # HTTP requests afterwards. If we don't delegate to TCP mode, we
            # should always negotiate a SSL connection.
            #
            # FIXME: Turns out the previous statement isn't entirely true.
            # Chrome on Windows CONNECTs to :80 if an explicit proxy is
            # configured and a websocket connection should be established. We
            # don't support websocket at the moment, so it fails anyway, but we
            # should come up with a better solution to this if we start to
            # support WebSockets.
            should_establish_ssl = (
                address.port in self.c.config.ssl_ports
                or
                not self.c.config.check_tcp(address)
            )

            if should_establish_ssl:
                self.c.log(
                    "Received CONNECT request to SSL port. "
                    "Upgrading to SSL...", "debug"
                )
                server_ssl = not self.c.config.no_upstream_cert
                if server_ssl:
                    self.c.establish_server_connection()
                self.c.establish_ssl(server=server_ssl, client=True)
                self.c.log("Upgrade to SSL completed.", "debug")

            if self.c.config.check_tcp(address):
                self.c.log(
                    "Generic TCP mode for host: %s:%s" % address(),
                    "info"
                )
                TCPHandler(self.c).handle_messages()
                return False

            return True

    def authenticate(self, request):
        if self.c.config.authenticator:
            if self.c.config.authenticator.authenticate(request.headers):
                self.c.config.authenticator.clean(request.headers)
            else:
                raise http.HttpAuthenticationError(
                    self.c.config.authenticator.auth_challenge_headers())
        return request.headers