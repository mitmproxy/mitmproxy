from __future__ import (absolute_import, print_function, division)

import sys
import traceback
import six

from netlib import tcp
from netlib.exceptions import HttpException, HttpReadDisconnect, NetlibException
from netlib.http import Headers

from h2.exceptions import H2Error

from .. import utils
from ..exceptions import HttpProtocolException, ProtocolException
from ..models import (
    HTTPFlow,
    HTTPResponse,
    make_error_response,
    make_connect_response,
    Error,
    expect_continue_response
)

from .base import Layer, Kill


class _HttpTransmissionLayer(Layer):

    def read_request(self):
        raise NotImplementedError()

    def read_request_body(self, request):
        raise NotImplementedError()

    def send_request(self, request):
        raise NotImplementedError()

    def read_response(self, request):
        response = self.read_response_headers()
        response.data.content = b"".join(
            self.read_response_body(request, response)
        )
        return response

    def read_response_headers(self):
        raise NotImplementedError()

    def read_response_body(self, request, response):
        raise NotImplementedError()
        yield "this is a generator"  # pragma: no cover

    def send_response(self, response):
        if response.content is None:
            raise HttpException("Cannot assemble flow with missing content")
        self.send_response_headers(response)
        self.send_response_body(response, [response.content])

    def send_response_headers(self, response):
        raise NotImplementedError()

    def send_response_body(self, response, chunks):
        raise NotImplementedError()

    def check_close_connection(self, flow):
        raise NotImplementedError()


class ConnectServerConnection(object):

    """
    "Fake" ServerConnection to represent state after a CONNECT request to an upstream proxy.
    """

    def __init__(self, address, ctx):
        self.address = tcp.Address.wrap(address)
        self._ctx = ctx

    @property
    def via(self):
        return self._ctx.server_conn

    def __getattr__(self, item):
        return getattr(self.via, item)

    def __bool__(self):
        return bool(self.via)

    if six.PY2:
        __nonzero__ = __bool__


class UpstreamConnectLayer(Layer):

    def __init__(self, ctx, connect_request):
        super(UpstreamConnectLayer, self).__init__(ctx)
        self.connect_request = connect_request
        self.server_conn = ConnectServerConnection(
            (connect_request.host, connect_request.port),
            self.ctx
        )

    def __call__(self):
        layer = self.ctx.next_layer(self)
        layer()

    def _send_connect_request(self):
        self.send_request(self.connect_request)
        resp = self.read_response(self.connect_request)
        if resp.status_code != 200:
            raise ProtocolException("Reconnect: Upstream server refuses CONNECT request")

    def connect(self):
        if not self.server_conn:
            self.ctx.connect()
            self._send_connect_request()
        else:
            pass  # swallow the message

    def change_upstream_proxy_server(self, address):
        if address != self.server_conn.via.address:
            self.ctx.set_server(address)

    def set_server(self, address, server_tls=None, sni=None):
        if self.ctx.server_conn:
            self.ctx.disconnect()
        address = tcp.Address.wrap(address)
        self.connect_request.host = address.host
        self.connect_request.port = address.port
        self.server_conn.address = address

        if server_tls:
            raise ProtocolException(
                "Cannot upgrade to TLS, no TLS layer on the protocol stack."
            )


class HttpLayer(Layer):

    def __init__(self, ctx, mode):
        super(HttpLayer, self).__init__(ctx)
        self.mode = mode

        self.__initial_server_conn = None
        "Contains the original destination in transparent mode, which needs to be restored"
        "if an inline script modified the target server for a single http request"
        # We cannot rely on server_conn.tls_established,
        # see https://github.com/mitmproxy/mitmproxy/issues/925
        self.__initial_server_tls = None

    def __call__(self):
        if self.mode == "transparent":
            self.__initial_server_tls = self._server_tls
            self.__initial_server_conn = self.server_conn
        while True:
            try:
                request = self.get_request_from_client()
                self.log("request", "debug", [repr(request)])

                # Handle Proxy Authentication
                # Proxy Authentication conceptually does not work in transparent mode.
                # We catch this misconfiguration on startup. Here, we sort out requests
                # after a successful CONNECT request (which do not need to be validated anymore)
                if self.mode != "transparent" and not self.authenticate(request):
                    return

                # Make sure that the incoming request matches our expectations
                self.validate_request(request)

                # Regular Proxy Mode: Handle CONNECT
                if self.mode == "regular" and request.first_line_format == "authority":
                    self.handle_regular_mode_connect(request)
                    return

            except HttpReadDisconnect:
                # don't throw an error for disconnects that happen before/between requests.
                return
            except NetlibException as e:
                self.send_error_response(400, repr(e))
                six.reraise(ProtocolException, ProtocolException(
                    "Error in HTTP connection: %s" % repr(e)), sys.exc_info()[2])

            try:
                flow = HTTPFlow(self.client_conn, self.server_conn, live=self)
                flow.request = request
                # set upstream auth
                if self.mode == "upstream" and self.config.upstream_auth is not None:
                    self.data.headers["Proxy-Authorization"] = self.config.upstream_auth
                self.process_request_hook(flow)

                if not flow.response:
                    self.establish_server_connection(flow)
                    self.get_response_from_server(flow)
                else:
                    # response was set by an inline script.
                    # we now need to emulate the responseheaders hook.
                    flow = self.channel.ask("responseheaders", flow)
                    if flow == Kill:
                        raise Kill()

                self.log("response", "debug", [repr(flow.response)])
                flow = self.channel.ask("response", flow)
                if flow == Kill:
                    raise Kill()
                self.send_response_to_client(flow)

                if self.check_close_connection(flow):
                    return

                # Handle 101 Switching Protocols
                # It may be useful to pass additional args (such as the upgrade header)
                # to next_layer in the future
                if flow.response.status_code == 101:
                    layer = self.ctx.next_layer(self)
                    layer()
                    return

                # Upstream Proxy Mode: Handle CONNECT
                if flow.request.first_line_format == "authority" and flow.response.status_code == 200:
                    self.handle_upstream_mode_connect(flow.request.copy())
                    return

            except (ProtocolException, NetlibException) as e:
                self.send_error_response(502, repr(e))

                if not flow.response:
                    flow.error = Error(str(e))
                    self.channel.ask("error", flow)
                    self.log(traceback.format_exc(), "debug")
                    return
                else:
                    six.reraise(ProtocolException, ProtocolException(
                        "Error in HTTP connection: %s" % repr(e)), sys.exc_info()[2])
            finally:
                if flow:
                    flow.live = False

    def get_request_from_client(self):
        request = self.read_request()
        if request.headers.get("expect", "").lower() == "100-continue":
            # TODO: We may have to use send_response_headers for HTTP2 here.
            self.send_response(expect_continue_response)
            request.headers.pop("expect")
            request.body = b"".join(self.read_request_body(request))
        return request

    def send_error_response(self, code, message):
        try:
            response = make_error_response(code, message)
            self.send_response(response)
        except (NetlibException, H2Error):
            self.log(traceback.format_exc(), "debug")

    def change_upstream_proxy_server(self, address):
        # Make set_upstream_proxy_server always available,
        # even if there's no UpstreamConnectLayer
        if address != self.server_conn.address:
            return self.set_server(address)

    def handle_regular_mode_connect(self, request):
        self.set_server((request.host, request.port))
        self.send_response(make_connect_response(request.data.http_version))
        layer = self.ctx.next_layer(self)
        layer()

    def handle_upstream_mode_connect(self, connect_request):
        layer = UpstreamConnectLayer(self, connect_request)
        layer()

    def send_response_to_client(self, flow):
        if not flow.response.stream:
            # no streaming:
            # we already received the full response from the server and can
            # send it to the client straight away.
            self.send_response(flow.response)
        else:
            # streaming:
            # First send the headers and then transfer the response incrementally
            self.send_response_headers(flow.response)
            chunks = self.read_response_body(
                flow.request,
                flow.response
            )
            if callable(flow.response.stream):
                chunks = flow.response.stream(chunks)
            self.send_response_body(flow.response, chunks)
            flow.response.timestamp_end = utils.timestamp()

    def get_response_from_server(self, flow):
        def get_response():
            self.send_request(flow.request)
            flow.response = self.read_response_headers()

        try:
            get_response()
        except NetlibException as v:
            self.log(
                "server communication error: %s" % repr(v),
                level="debug"
            )
            # In any case, we try to reconnect at least once. This is
            # necessary because it might be possible that we already
            # initiated an upstream connection after clientconnect that
            # has already been expired, e.g consider the following event
            # log:
            # > clientconnect (transparent mode destination known)
            # > serverconnect (required for client tls handshake)
            # > read n% of large request
            # > server detects timeout, disconnects
            # > read (100-n)% of large request
            # > send large request upstream
            self.disconnect()
            self.connect()
            get_response()

        # call the appropriate script hook - this is an opportunity for an
        # inline script to set flow.stream = True
        flow = self.channel.ask("responseheaders", flow)
        if flow == Kill:
            raise Kill()

        if flow.response.stream:
            flow.response.data.content = None
        else:
            flow.response.data.content = b"".join(self.read_response_body(
                flow.request,
                flow.response
            ))
        flow.response.timestamp_end = utils.timestamp()

        # no further manipulation of self.server_conn beyond this point
        # we can safely set it as the final attribute value here.
        flow.server_conn = self.server_conn

    def process_request_hook(self, flow):
        # Determine .scheme, .host and .port attributes for inline scripts.
        # For absolute-form requests, they are directly given in the request.
        # For authority-form requests, we only need to determine the request scheme.
        # For relative-form requests, we need to determine host and port as
        # well.
        if self.mode == "regular":
            pass  # only absolute-form at this point, nothing to do here.
        elif self.mode == "upstream":
            if flow.request.first_line_format == "authority":
                flow.request.scheme = "http"  # pseudo value
        else:
            # Setting request.host also updates the host header, which we want to preserve
            host_header = flow.request.headers.get("host", None)
            flow.request.host = self.__initial_server_conn.address.host
            flow.request.port = self.__initial_server_conn.address.port
            if host_header:
                flow.request.headers["host"] = host_header
            flow.request.scheme = "https" if self.__initial_server_tls else "http"

        request_reply = self.channel.ask("request", flow)
        if request_reply == Kill:
            raise Kill()
        if isinstance(request_reply, HTTPResponse):
            flow.response = request_reply
            return

    def establish_server_connection(self, flow):
        address = tcp.Address((flow.request.host, flow.request.port))
        tls = (flow.request.scheme == "https")

        if self.mode == "regular" or self.mode == "transparent":
            # If there's an existing connection that doesn't match our expectations, kill it.
            if address != self.server_conn.address or tls != self.server_conn.tls_established:
                self.set_server(address, tls, address.host)
            # Establish connection is neccessary.
            if not self.server_conn:
                self.connect()
        else:
            if not self.server_conn:
                self.connect()
            if tls:
                raise HttpProtocolException("Cannot change scheme in upstream proxy mode.")
            """
            # This is a very ugly (untested) workaround to solve a very ugly problem.
            if self.server_conn and self.server_conn.tls_established and not ssl:
                self.disconnect()
                self.connect()
            elif ssl and not hasattr(self, "connected_to") or self.connected_to != address:
                if self.server_conn.tls_established:
                    self.disconnect()
                    self.connect()

                self.send_request(make_connect_request(address))
                tls_layer = TlsLayer(self, False, True)
                tls_layer._establish_tls_with_server()
            """

    def validate_request(self, request):
        if request.first_line_format == "absolute" and request.scheme != "http":
            raise HttpException("Invalid request scheme: %s" % request.scheme)

        expected_request_forms = {
            "regular": ("authority", "absolute",),
            "upstream": ("authority", "absolute"),
            "transparent": ("relative",)
        }

        allowed_request_forms = expected_request_forms[self.mode]
        if request.first_line_format not in allowed_request_forms:
            err_message = "Invalid HTTP request form (expected: %s, got: %s)" % (
                " or ".join(allowed_request_forms), request.first_line_format
            )
            raise HttpException(err_message)

        if self.mode == "regular" and request.first_line_format == "absolute":
            request.first_line_format = "relative"

    def authenticate(self, request):
        if self.config.authenticator:
            if self.config.authenticator.authenticate(request.headers):
                self.config.authenticator.clean(request.headers)
            else:
                self.send_response(make_error_response(
                    407,
                    "Proxy Authentication Required",
                    Headers(**self.config.authenticator.auth_challenge_headers())
                ))
                return False
        return True
