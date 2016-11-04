import h2.exceptions
import time
import traceback
from mitmproxy import exceptions
from mitmproxy import http
from mitmproxy import flow
from mitmproxy.proxy.protocol import base
from mitmproxy.proxy.protocol import websockets as pwebsockets
import mitmproxy.net.http
from mitmproxy.net import tcp
from mitmproxy.net import websockets


class _HttpTransmissionLayer(base.Layer):
    def read_request_headers(self, flow):
        raise NotImplementedError()

    def read_request_body(self, request):
        raise NotImplementedError()

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
            raise exceptions.HttpException("Cannot assemble flow with missing content")
        self.send_response_headers(response)
        self.send_response_body(response, [response.data.content])

    def send_response_headers(self, response):
        raise NotImplementedError()

    def send_response_body(self, response, chunks):
        raise NotImplementedError()

    def check_close_connection(self, f):
        raise NotImplementedError()


class ConnectServerConnection:

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

    def connected(self):
        return self.via.connected()


class UpstreamConnectLayer(base.Layer):

    def __init__(self, ctx, connect_request):
        super().__init__(ctx)
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
        if not self.server_conn.connected():
            self.ctx.connect()
            self._send_connect_request()
        else:
            pass  # swallow the message

    def change_upstream_proxy_server(self, address):
        if address != self.server_conn.via.address:
            self.ctx.set_server(address)

    def set_server(self, address):
        if self.ctx.server_conn.connected():
            self.ctx.disconnect()
        address = tcp.Address.wrap(address)
        self.connect_request.host = address.host
        self.connect_request.port = address.port
        self.server_conn.address = address


FIRSTLINES = set(["absolute", "relative", "authority"])
# At this point, we see only a subset of the proxy modes
MODES = set(["regular", "transparent", "upstream"])
MODE_REQUEST_FORMS = {
    "regular": ("authority", "absolute"),
    "transparent": ("relative"),
    "upstream": ("authority", "absolute"),
}


def validate_request_form(mode, request):
    if request.first_line_format == "absolute" and request.scheme != "http":
        raise exceptions.HttpException("Invalid request scheme: %s" % request.scheme)
    allowed_request_forms = MODE_REQUEST_FORMS[mode]
    if request.first_line_format not in allowed_request_forms:
        err_message = "Invalid HTTP request form (expected: %s, got: %s)" % (
            " or ".join(allowed_request_forms), request.first_line_format
        )
        raise exceptions.HttpException(err_message)


class HttpLayer(base.Layer):

    def __init__(self, ctx, mode):
        super().__init__(ctx)
        if mode not in MODES:
            raise exceptions.ServerException("Invalid mode: %s"%mode)
        self.mode = mode
        self.__initial_server_conn = None
        "Contains the original destination in transparent mode, which needs to be restored"
        "if an inline script modified the target server for a single http request"
        # We cannot rely on server_conn.tls_established,
        # see https://github.com/mitmproxy/mitmproxy/issues/925
        self.__initial_server_tls = None
        # Requests happening after CONNECT do not need Proxy-Authorization headers.
        self.connect_request = False

    def __call__(self):
        if self.mode == "transparent":
            self.__initial_server_tls = self.server_tls
            self.__initial_server_conn = self.server_conn
        while True:
            flow = http.HTTPFlow(self.client_conn, self.server_conn, live=self)
            if not self._process_flow(flow):
                return

    def _process_flow(self, f):
        try:
            request = self.read_request_headers(f)
            request.data.content = b"".join(self.read_request_body(request))
            request.timestamp_end = time.time()
            f.request = request
            self.channel.ask("requestheaders", f)
            if request.headers.get("expect", "").lower() == "100-continue":
                # TODO: We may have to use send_response_headers for HTTP2 here.
                self.send_response(http.expect_continue_response)
                request.headers.pop("expect")
                request.content = b"".join(self.read_request_body(request))
                request.timestamp_end = time.time()

            validate_request_form(self.mode, request)

            if self.mode == "regular" and request.first_line_format == "absolute":
                request.first_line_format = "relative"

        except exceptions.HttpReadDisconnect:
            # don't throw an error for disconnects that happen before/between requests.
            return False
        except exceptions.HttpException as e:
            # We optimistically guess there might be an HTTP client on the
            # other end
            self.send_error_response(400, repr(e))
            raise exceptions.ProtocolException(
                "HTTP protocol error in client request: {}".format(e)
            )

        self.log("request", "debug", [repr(request)])

        # Handle Proxy Authentication
        # Proxy Authentication conceptually does not work in transparent mode.
        # We catch this misconfiguration on startup. Here, we sort out requests
        # after a successful CONNECT request (which do not need to be validated anymore)
        if not self.connect_request and not self.authenticate(request):
            return False

        f.request = request

        try:
            # Regular Proxy Mode: Handle CONNECT
            if self.mode == "regular" and request.first_line_format == "authority":
                self.connect_request = True
                self.set_server((request.host, request.port))
                self.send_response(http.make_connect_response(request.data.http_version))
                layer = self.ctx.next_layer(self)
                layer()
                return False
        except (exceptions.ProtocolException, exceptions.NetlibException) as e:
            # HTTPS tasting means that ordinary errors like resolution and
            # connection errors can happen here.
            self.send_error_response(502, repr(e))
            f.error = flow.Error(str(e))
            self.channel.ask("error", f)
            return False

        # update host header in reverse proxy mode
        if self.config.options.mode == "reverse":
            f.request.headers["Host"] = self.config.upstream_server.address.host

        # set upstream auth
        if self.mode == "upstream" and self.config.upstream_auth is not None:
            f.request.headers["Proxy-Authorization"] = self.config.upstream_auth

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
            host_header = f.request.headers.get("host", None)
            f.request.host = self.__initial_server_conn.address.host
            f.request.port = self.__initial_server_conn.address.port
            if host_header:
                f.request.headers["host"] = host_header
            f.request.scheme = "https" if self.__initial_server_tls else "http"
        self.channel.ask("request", f)

        try:
            if websockets.check_handshake(request.headers) and websockets.check_client_version(request.headers):
                # We only support RFC6455 with WebSockets version 13
                # allow inline scripts to manipulate the client handshake
                self.channel.ask("websocket_handshake", f)

            if not f.response:
                self.establish_server_connection(
                    f.request.host,
                    f.request.port,
                    f.request.scheme
                )

                def get_response():
                    self.send_request(f.request)
                    f.response = self.read_response_headers()

                try:
                    get_response()
                except exceptions.NetlibException as e:
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
                        raise exceptions.ProtocolException(
                            "First and only attempt to get response via HTTP2 failed."
                        )

                    self.disconnect()
                    self.connect()
                    get_response()

                # call the appropriate script hook - this is an opportunity for an
                # inline script to set f.stream = True
                self.channel.ask("responseheaders", f)

                if f.response.stream:
                    f.response.data.content = None
                else:
                    f.response.data.content = b"".join(self.read_response_body(
                        f.request,
                        f.response
                    ))
                f.response.timestamp_end = time.time()

                # no further manipulation of self.server_conn beyond this point
                # we can safely set it as the final attribute value here.
                f.server_conn = self.server_conn
            else:
                # response was set by an inline script.
                # we now need to emulate the responseheaders hook.
                self.channel.ask("responseheaders", f)

            self.log("response", "debug", [repr(f.response)])
            self.channel.ask("response", f)

            if not f.response.stream:
                # no streaming:
                # we already received the full response from the server and can
                # send it to the client straight away.
                self.send_response(f.response)
            else:
                # streaming:
                # First send the headers and then transfer the response incrementally
                self.send_response_headers(f.response)
                chunks = self.read_response_body(
                    f.request,
                    f.response
                )
                if callable(f.response.stream):
                    chunks = f.response.stream(chunks)
                self.send_response_body(f.response, chunks)
                f.response.timestamp_end = time.time()

            if self.check_close_connection(f):
                return False

            # Handle 101 Switching Protocols
            if f.response.status_code == 101:
                """
                    Handle a successful HTTP 101 Switching Protocols Response, received after
                    e.g. a WebSocket upgrade request.
                """
                # Check for WebSockets handshake
                is_websockets = (
                    websockets.check_handshake(f.request.headers) and
                    websockets.check_handshake(f.response.headers)
                )
                if is_websockets and not self.config.options.websockets:
                    self.log(
                        "Client requested WebSocket connection, but the protocol is disabled.",
                        "info"
                    )

                if is_websockets and self.config.options.websockets:
                    layer = pwebsockets.WebSocketsLayer(self, f)
                else:
                    layer = self.ctx.next_layer(self)
                layer()
                return False  # should never be reached

            # Upstream Proxy Mode: Handle CONNECT
            if f.request.first_line_format == "authority" and f.response.status_code == 200:
                layer = UpstreamConnectLayer(self, f.request)
                layer()
                return False

        except (exceptions.ProtocolException, exceptions.NetlibException) as e:
            self.send_error_response(502, repr(e))
            if not f.response:
                f.error = flow.Error(str(e))
                self.channel.ask("error", f)
                return False
            else:
                raise exceptions.ProtocolException(
                    "Error in HTTP connection: %s" % repr(e)
                )
        finally:
            if f:
                f.live = False

        return True

    def send_error_response(self, code, message, headers=None) -> None:
        try:
            response = http.make_error_response(code, message, headers)
            self.send_response(response)
        except (exceptions.NetlibException, h2.exceptions.H2Error, exceptions.Http2ProtocolException):
            self.log(traceback.format_exc(), "debug")

    def change_upstream_proxy_server(self, address) -> None:
        # Make set_upstream_proxy_server always available,
        # even if there's no UpstreamConnectLayer
        if address != self.server_conn.address:
            self.set_server(address)

    def establish_server_connection(self, host: str, port: int, scheme: str):
        address = tcp.Address((host, port))
        tls = (scheme == "https")

        if self.mode == "regular" or self.mode == "transparent":
            # If there's an existing connection that doesn't match our expectations, kill it.
            if address != self.server_conn.address or tls != self.server_tls:
                self.set_server(address)
                self.set_server_tls(tls, address.host)
            # Establish connection is neccessary.
            if not self.server_conn.connected():
                self.connect()
        else:
            if not self.server_conn.connected():
                self.connect()
            if tls:
                raise exceptions.HttpProtocolException("Cannot change scheme in upstream proxy mode.")

    def authenticate(self, request) -> bool:
        if self.config.authenticator:
            if self.config.authenticator.authenticate(request.headers):
                self.config.authenticator.clean(request.headers)
            else:
                if self.mode == "transparent":
                    self.send_response(http.make_error_response(
                        401,
                        "Authentication Required",
                        mitmproxy.net.http.Headers(**self.config.authenticator.auth_challenge_headers())
                    ))
                else:
                    self.send_response(http.make_error_response(
                        407,
                        "Proxy Authentication Required",
                        mitmproxy.net.http.Headers(**self.config.authenticator.auth_challenge_headers())
                    ))
                return False
        return True
