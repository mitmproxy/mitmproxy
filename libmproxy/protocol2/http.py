from __future__ import (absolute_import, print_function, division)

from .. import version
from ..exceptions import InvalidCredentials, HttpException, ProtocolException
from .layer import Layer, ServerConnectionMixin
from libmproxy import utils
from .messages import SetServer, Connect, Reconnect, Kill
from libmproxy.protocol import KILL

from libmproxy.protocol.http import HTTPFlow
from libmproxy.protocol.http_wrappers import HTTPResponse, HTTPRequest
from libmproxy.protocol2.tls import TlsLayer
from netlib import tcp
from netlib.http import status_codes, http1, HttpErrorConnClosed
from netlib.http.semantics import CONTENT_MISSING
from netlib import odict
from netlib.tcp import NetLibError
from netlib.http.http1 import HTTP1Protocol
from netlib.http.http2 import HTTP2Protocol

class Http1Layer(Layer):
    def __init__(self, ctx, mode):
        super(Http1Layer, self).__init__(ctx)
        self.mode = mode
        self.client_protocol = HTTP1Protocol(self.client_conn)
        self.server_protocol = HTTP1Protocol(self.server_conn)

    def __call__(self):
        from .http import HttpLayer
        layer = HttpLayer(self, self.mode)
        for message in layer():
            yield message


class Http2Layer(Layer):
    def __init__(self, ctx, mode):
        super(Http2Layer, self).__init__(ctx)
        self.mode = mode
        self.client_protocol = HTTP2Protocol(self.client_conn, is_server=True)
        self.server_protocol = HTTP2Protocol(self.server_conn, is_server=False)

    def __call__(self):
        from .http import HttpLayer
        layer = HttpLayer(self, self.mode)
        for message in layer():
            yield message

def make_error_response(status_code, message, headers=None):
    response = status_codes.RESPONSES.get(status_code, "Unknown")
    body = """
        <html>
            <head>
                <title>%d %s</title>
            </head>
            <body>%s</body>
        </html>
    """.strip() % (status_code, response, message)

    if not headers:
        headers = odict.ODictCaseless()
    headers["Server"] = [version.NAMEVERSION]
    headers["Connection"] = ["close"]
    headers["Content-Length"] = [len(body)]
    headers["Content-Type"] = ["text/html"]

    return HTTPResponse(
        (1, 1),  # FIXME: Should be a string.
        status_code,
        response,
        headers,
        body,
    )


def make_connect_request(address):
    return HTTPRequest(
        "authority", "CONNECT", None, address.host, address.port, None, (1, 1),
        odict.ODictCaseless(), ""
    )


def make_connect_response(httpversion):
    headers = odict.ODictCaseless([
        ["Content-Length", "0"],
        ["Proxy-Agent", version.NAMEVERSION]
    ])
    return HTTPResponse(
        httpversion,
        200,
        "Connection established",
        headers,
        "",
    )


class HttpLayer(Layer):
    """
    HTTP 1 Layer
    """

    def __init__(self, ctx, mode):
        super(HttpLayer, self).__init__(ctx)
        self.mode = mode

    def __call__(self):
        while True:
            try:
                try:
                    request = HTTPRequest.from_protocol(
                        self.client_protocol,
                        body_size_limit=self.config.body_size_limit
                    )
                except tcp.NetLibError:
                    # don't throw an error for disconnects that happen
                    # before/between requests.
                    return

                self.log("request", "debug", [repr(request)])

                # Handle Proxy Authentication
                self.authenticate(request)

                # Regular Proxy Mode: Handle CONNECT
                if self.mode == "regular" and request.form_in == "authority":
                    yield SetServer((request.host, request.port), False, None)
                    self.send_to_client(make_connect_response(request.httpversion))
                    layer = self.ctx.next_layer(self)
                    for message in layer():
                        if not self._handle_server_message(message):
                            yield message
                    return

                # Make sure that the incoming request matches our expectations
                self.validate_request(request)

                flow = HTTPFlow(self.client_conn, self.server_conn)
                flow.request = request
                for message in self.process_request_hook(flow):
                    yield message

                if not flow.response:
                    for message in self.establish_server_connection(flow):
                        yield message
                    for message in self.get_response_from_server(flow):
                        yield message

                self.send_response_to_client(flow)

                if self.check_close_connection(flow):
                    return

                if flow.request.form_in == "authority" and flow.response.code == 200:
                    raise NotImplementedError("Upstream mode CONNECT not implemented")
            except (HttpErrorConnClosed, NetLibError) as e:
                make_error_response(502, repr(e))
                raise ProtocolException(repr(e), e)

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
        if flow.request.form_in == "authority" and flow.response.code == 200:
            # Workaround for
            # https://github.com/mitmproxy/mitmproxy/issues/313: Some
            # proxies (e.g. Charles) send a CONNECT response with HTTP/1.0
            # and no Content-Length header

            return False
        return close_connection

    def send_response_to_client(self, flow):
        if not flow.response.stream:
            # no streaming:
            # we already received the full response from the server and can
            # send it to the client straight away.
            self.send_to_client(flow.response)
        else:
            # streaming:
            # First send the headers and then transfer the response
            # incrementally:
            h = self.client_protocol._assemble_response_first_line(flow.response)
            self.send_to_client(h + "\r\n")
            h = self.client_protocol._assemble_response_headers(flow.response, preserve_transfer_encoding=True)
            self.send_to_client(h + "\r\n")

            chunks = self.client_protocol.read_http_body_chunked(
                flow.response.headers,
                self.config.body_size_limit,
                flow.request.method,
                flow.response.code,
                False,
                4096
            )

            if callable(flow.response.stream):
                chunks = flow.response.stream(chunks)

            for chunk in chunks:
                for part in chunk:
                    self.send_to_client(part)
                self.client_conn.wfile.flush()

            flow.response.timestamp_end = utils.timestamp()

    def get_response_from_server(self, flow):
        # TODO: Add second attempt.
        self.send_to_server(flow.request)

        flow.response = HTTPResponse.from_protocol(
            self.server_protocol,
            flow.request.method,
            body_size_limit=self.config.body_size_limit,
            include_body=False,
        )

        # call the appropriate script hook - this is an opportunity for an
        # inline script to set flow.stream = True
        flow = self.channel.ask("responseheaders", flow)
        if flow is None or flow == KILL:
            yield Kill()

        if flow.response.stream:
            flow.response.content = CONTENT_MISSING
        elif isinstance(self.server_protocol, http1.HTTP1Protocol):
            flow.response.content = self.server_protocol.read_http_body(
                self.server_conn,
                flow.response.headers,
                self.config.body_size_limit,
                flow.request.method,
                flow.response.code,
                False
            )
            flow.response.timestamp_end = utils.timestamp()

        # no further manipulation of self.server_conn beyond this point
        # we can safely set it as the final attribute value here.
        flow.server_conn = self.server_conn

        self.log(
            "response",
            "debug",
            [repr(flow.response)]
        )
        response_reply = self.channel.ask("response", flow)
        if response_reply is None or response_reply == KILL:
            yield Kill()

    def process_request_hook(self, flow):
        # Determine .scheme, .host and .port attributes for inline scripts.
        # For absolute-form requests, they are directly given in the request.
        # For authority-form requests, we only need to determine the request scheme.
        # For relative-form requests, we need to determine host and port as
        # well.
        if self.mode == "regular":
            pass  # only absolute-form at this point, nothing to do here.
        elif self.mode == "upstream":
            if flow.request.form_in == "authority":
                flow.request.scheme = "http"  # pseudo value
        else:
            flow.request.host = self.ctx.server_address.host
            flow.request.port = self.ctx.server_address.port
            flow.request.scheme = "https" if self.server_conn.tls_established else "http"

        # TODO: Expose ChangeServer functionality to inline scripts somehow? (yield_from_callback?)
        request_reply = self.channel.ask("request", flow)
        if request_reply is None or request_reply == KILL:
            yield Kill()
        if isinstance(request_reply, HTTPResponse):
            flow.response = request_reply
            return

    def establish_server_connection(self, flow):

        address = tcp.Address((flow.request.host, flow.request.port))
        tls = (flow.request.scheme == "https")
        if self.mode == "regular" or self.mode == "transparent":
            # If there's an existing connection that doesn't match our expectations, kill it.
            if self.server_address != address or tls != self.server_conn.ssl_established:
                yield SetServer(address, tls, address.host)
            # Establish connection is neccessary.
            if not self.server_conn:
                yield Connect()

            # ChangeServer is not guaranteed to work with TLS:
            # If there's not TlsLayer below which could catch the exception,
            # TLS will not be established.
            if tls and not self.server_conn.tls_established:
                raise ProtocolException("Cannot upgrade to SSL, no TLS layer on the protocol stack.")

        else:
            if tls:
                raise HttpException("Cannot change scheme in upstream proxy mode.")
            """
            # This is a very ugly (untested) workaround to solve a very ugly problem.
            # FIXME: Check if connected first.
            if self.server_conn.tls_established and not ssl:
                yield Reconnect()
            elif ssl and not hasattr(self, "connected_to") or self.connected_to != address:
                if self.server_conn.tls_established:
                    yield Reconnect()

                self.send_to_server(make_connect_request(address))
                tls_layer = TlsLayer(self, False, True)
                tls_layer._establish_tls_with_server()
            """

    def validate_request(self, request):
        if request.form_in == "absolute" and request.scheme != "http":
            self.send_resplonse(make_error_response(400, "Invalid request scheme: %s" % request.scheme))
            raise HttpException("Invalid request scheme: %s" % request.scheme)

        expected_request_forms = {
            "regular": ("absolute",),  # an authority request would already be handled.
            "upstream": ("authority", "absolute"),
            "transparent": ("relative",)
        }

        allowed_request_forms = expected_request_forms[self.mode]
        if request.form_in not in allowed_request_forms:
            err_message = "Invalid HTTP request form (expected: %s, got: %s)" % (
                " or ".join(allowed_request_forms), request.form_in
            )
            self.send_to_client(make_error_response(400, err_message))
            raise HttpException(err_message)

        if self.mode == "regular":
            request.form_out = "relative"

    def authenticate(self, request):
        if self.config.authenticator:
            if self.config.authenticator.authenticate(request.headers):
                self.config.authenticator.clean(request.headers)
            else:
                self.send_to_client(make_error_response(
                    407,
                    "Proxy Authentication Required",
                    self.config.authenticator.auth_challenge_headers()
                ))
                raise InvalidCredentials("Proxy Authentication Required")

    def send_to_server(self, message):
        self.server_conn.send(self.server_protocol.assemble(message))

    def send_to_client(self, message):
        # FIXME
        # - possibly do some http2 stuff here
        self.client_conn.send(self.client_protocol.assemble(message))
