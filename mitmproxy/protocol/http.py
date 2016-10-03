from __future__ import absolute_import, print_function, division

import h2.exceptions
import netlib.exceptions
import six
import sys
import time
import traceback
from mitmproxy import exceptions
from mitmproxy import models
from mitmproxy.protocol import base
from mitmproxy.protocol import websockets as pwebsockets
from netlib import http
from netlib import tcp
from netlib import websockets


class _HttpTransmissionLayer(base.Layer):
    def read_request_headers(self):
        raise NotImplementedError()

    def read_request_body(self, request):
        raise NotImplementedError()

    def read_request(self):
        request = self.read_request_headers()
        request.data.content = b"".join(
            self.read_request_body(request)
        )
        request.timestamp_end = time.time()
        return request

    def send_request(self, request):
        raise NotImplementedError()

    def read_response_headers(self):
        raise NotImplementedError()

    def read_response_body(self, request, response):
        raise NotImplementedError()
        yield "this is a generator"  # pragma: no cover

    def read_response(self, request):
        response = self.read_response_headers()
        response.data.content = b"".join(
            self.read_response_body(request, response)
        )
        return response

    def send_response(self, response):
        if response.data.content is None:
            raise netlib.exceptions.HttpException("Cannot assemble flow with missing content")
        self.send_response_headers(response)
        self.send_response_body(response, [response.data.content])

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


class UpstreamConnectLayer(base.Layer):

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
            raise exceptions.ProtocolException("Reconnect: Upstream server refuses CONNECT request")

    def connect(self):
        if not self.server_conn:
            self.ctx.connect()
            self._send_connect_request()
        else:
            pass  # swallow the message

    def change_upstream_proxy_server(self, address):
        if address != self.server_conn.via.address:
            self.ctx.set_server(address)

    def set_server(self, address):
        if self.ctx.server_conn:
            self.ctx.disconnect()
        address = tcp.Address.wrap(address)
        self.connect_request.host = address.host
        self.connect_request.port = address.port
        self.server_conn.address = address


class HttpLayer(base.Layer):

    def __init__(self, ctx, mode):
        super(HttpLayer, self).__init__(ctx)
        self.mode = mode

        self.__initial_server_conn = None
        "Contains the original destination in transparent mode, which needs to be restored"
        "if an inline script modified the target server for a single http request"
        # We cannot rely on server_conn.tls_established,
        # see https://github.com/mitmproxy/mitmproxy/issues/925
        self.__initial_server_tls = None
        # Requests happening after CONNECT do not need Proxy-Authorization headers.
        self.http_authenticated = False

    def __call__(self):
        if self.mode == "transparent":
            self.__initial_server_tls = self.server_tls
            self.__initial_server_conn = self.server_conn
        while True:
            flow = models.HTTPFlow(self.client_conn, self.server_conn, live=self)
            try:
                request = self.get_request_from_client(flow)
                # Make sure that the incoming request matches our expectations
                self.validate_request(request)
            except netlib.exceptions.HttpReadDisconnect:
                # don't throw an error for disconnects that happen before/between requests.
                return
            except netlib.exceptions.HttpException as e:
                # We optimistically guess there might be an HTTP client on the
                # other end
                self.send_error_response(400, repr(e))
                six.reraise(
                    exceptions.ProtocolException,
                    exceptions.ProtocolException(
                        "HTTP protocol error in client request: {}".format(e)
                    ),
                    sys.exc_info()[2]
                )

            self.log("request", "debug", [repr(request)])

            # Handle Proxy Authentication
            # Proxy Authentication conceptually does not work in transparent mode.
            # We catch this misconfiguration on startup. Here, we sort out requests
            # after a successful CONNECT request (which do not need to be validated anymore)
            if not (self.http_authenticated or self.authenticate(request)):
                return

            flow.request = request

            try:
                # Regular Proxy Mode: Handle CONNECT
                if self.mode == "regular" and request.first_line_format == "authority":
                    self.handle_regular_mode_connect(request)
                    return
            except (exceptions.ProtocolException, netlib.exceptions.NetlibException) as e:
                # HTTPS tasting means that ordinary errors like resolution and
                # connection errors can happen here.
                self.send_error_response(502, repr(e))
                flow.error = models.Error(str(e))
                self.channel.ask("error", flow)
                return

            # update host header in reverse proxy mode
            if self.config.options.mode == "reverse":
                if six.PY2:
                    flow.request.headers["Host"] = self.config.upstream_server.address.host.encode()
                else:
                    flow.request.headers["Host"] = self.config.upstream_server.address.host

            # set upstream auth
            if self.mode == "upstream" and self.config.upstream_auth is not None:
                flow.request.headers["Proxy-Authorization"] = self.config.upstream_auth
            self.process_request_hook(flow)

            try:
                if websockets.check_handshake(request.headers) and websockets.check_client_version(request.headers):
                    # We only support RFC6455 with WebSockets version 13
                    # allow inline scripts to manipulate the client handshake
                    self.channel.ask("websocket_handshake", flow)

                if not flow.response:
                    self.establish_server_connection(
                        flow.request.host,
                        flow.request.port,
                        flow.request.scheme
                    )
                    self.get_response_from_server(flow)
                else:
                    # response was set by an inline script.
                    # we now need to emulate the responseheaders hook.
                    self.channel.ask("responseheaders", flow)

                self.log("response", "debug", [repr(flow.response)])
                self.channel.ask("response", flow)
                self.send_response_to_client(flow)

                if self.check_close_connection(flow):
                    return

                # Handle 101 Switching Protocols
                if flow.response.status_code == 101:
                    return self.handle_101_switching_protocols(flow)

                # Upstream Proxy Mode: Handle CONNECT
                if flow.request.first_line_format == "authority" and flow.response.status_code == 200:
                    self.handle_upstream_mode_connect(flow.request.copy())
                    return

            except (exceptions.ProtocolException, netlib.exceptions.NetlibException) as e:
                self.send_error_response(502, repr(e))
                if not flow.response:
                    flow.error = models.Error(str(e))
                    self.channel.ask("error", flow)
                    return
                else:
                    six.reraise(exceptions.ProtocolException, exceptions.ProtocolException(
                        "Error in HTTP connection: %s" % repr(e)), sys.exc_info()[2])
            finally:
                if flow:
                    flow.live = False

    def get_request_from_client(self, flow):
        request = self.read_request()
        flow.request = request
        self.channel.ask("requestheaders", flow)
        if request.headers.get("expect", "").lower() == "100-continue":
            # TODO: We may have to use send_response_headers for HTTP2 here.
            self.send_response(models.expect_continue_response)
            request.headers.pop("expect")
            request.body = b"".join(self.read_request_body(request))
            request.timestamp_end = time.time()
        return request

    def send_error_response(self, code, message, headers=None):
        try:
            response = models.make_error_response(code, message, headers)
            self.send_response(response)
        except (netlib.exceptions.NetlibException, h2.exceptions.H2Error, exceptions.Http2ProtocolException):
            self.log(traceback.format_exc(), "debug")

    def change_upstream_proxy_server(self, address):
        # Make set_upstream_proxy_server always available,
        # even if there's no UpstreamConnectLayer
        if address != self.server_conn.address:
            return self.set_server(address)

    def handle_regular_mode_connect(self, request):
        self.http_authenticated = True
        self.set_server((request.host, request.port))
        self.send_response(models.make_connect_response(request.data.http_version))
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
            flow.response.timestamp_end = time.time()

    def get_response_from_server(self, flow):
        def get_response():
            self.send_request(flow.request)
            flow.response = self.read_response_headers()

        try:
            get_response()
        except netlib.exceptions.NetlibException as e:
            self.log(
                "server communication error: %s" % repr(e),
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

            if isinstance(e, exceptions.Http2ProtocolException):
                # do not try to reconnect for HTTP2
                raise exceptions.ProtocolException("First and only attempt to get response via HTTP2 failed.")

            self.disconnect()
            self.connect()
            get_response()

        # call the appropriate script hook - this is an opportunity for an
        # inline script to set flow.stream = True
        self.channel.ask("responseheaders", flow)

        if flow.response.stream:
            flow.response.data.content = None
        else:
            flow.response.data.content = b"".join(self.read_response_body(
                flow.request,
                flow.response
            ))
        flow.response.timestamp_end = time.time()

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
            pass
        else:
            # Setting request.host also updates the host header, which we want to preserve
            host_header = flow.request.headers.get("host", None)
            flow.request.host = self.__initial_server_conn.address.host
            flow.request.port = self.__initial_server_conn.address.port
            if host_header:
                flow.request.headers["host"] = host_header
            flow.request.scheme = "https" if self.__initial_server_tls else "http"
        self.channel.ask("request", flow)

    def establish_server_connection(self, host, port, scheme):
        address = tcp.Address((host, port))
        tls = (scheme == "https")

        if self.mode == "regular" or self.mode == "transparent":
            # If there's an existing connection that doesn't match our expectations, kill it.
            if address != self.server_conn.address or tls != self.server_tls:
                self.set_server(address)
                self.set_server_tls(tls, address.host)
            # Establish connection is neccessary.
            if not self.server_conn:
                self.connect()
        else:
            if not self.server_conn:
                self.connect()
            if tls:
                raise exceptions.HttpProtocolException("Cannot change scheme in upstream proxy mode.")
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
            raise netlib.exceptions.HttpException("Invalid request scheme: %s" % request.scheme)

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
            raise netlib.exceptions.HttpException(err_message)

        if self.mode == "regular" and request.first_line_format == "absolute":
            request.first_line_format = "relative"

    def authenticate(self, request):
        if self.config.authenticator:
            if self.config.authenticator.authenticate(request.headers):
                self.config.authenticator.clean(request.headers)
            else:
                if self.mode == "transparent":
                    self.send_response(models.make_error_response(
                        401,
                        "Authentication Required",
                        http.Headers(**self.config.authenticator.auth_challenge_headers())
                    ))
                else:
                    self.send_response(models.make_error_response(
                        407,
                        "Proxy Authentication Required",
                        http.Headers(**self.config.authenticator.auth_challenge_headers())
                    ))
                return False
        return True

    def handle_101_switching_protocols(self, flow):
        """
        Handle a successful HTTP 101 Switching Protocols Response, received after e.g. a WebSocket upgrade request.
        """
        # Check for WebSockets handshake
        is_websockets = (
            flow and
            websockets.check_handshake(flow.request.headers) and
            websockets.check_handshake(flow.response.headers)
        )
        if is_websockets and not self.config.options.websockets:
            self.log(
                "Client requested WebSocket connection, but the protocol is currently disabled in mitmproxy.",
                "info"
            )

        if is_websockets and self.config.options.websockets:
            layer = pwebsockets.WebSocketsLayer(self, flow)
        else:
            layer = self.ctx.next_layer(self)

        layer()
