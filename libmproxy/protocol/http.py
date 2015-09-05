from __future__ import (absolute_import, print_function, division)

from netlib import tcp
from netlib.http import http1, HttpErrorConnClosed, HttpError, Headers
from netlib.http.semantics import CONTENT_MISSING
from netlib import odict
from netlib.tcp import NetLibError, Address
from netlib.http.http1 import HTTP1Protocol
from netlib.http.http2 import HTTP2Protocol
from netlib.http.http2.frame import GoAwayFrame, PriorityFrame, WindowUpdateFrame

from .. import utils
from ..exceptions import InvalidCredentials, HttpException, ProtocolException
from ..models import (
    HTTPFlow, HTTPRequest, HTTPResponse, make_error_response, make_connect_response, Error
)
from .base import Layer, Kill


class _HttpLayer(Layer):
    supports_streaming = False

    def read_request(self):
        raise NotImplementedError()

    def send_request(self, request):
        raise NotImplementedError()

    def read_response(self, request_method):
        raise NotImplementedError()

    def send_response(self, response):
        raise NotImplementedError()

    def check_close_connection(self, flow):
        raise NotImplementedError()


class _StreamingHttpLayer(_HttpLayer):
    supports_streaming = True

    def read_response_headers(self):
        raise NotImplementedError

    def read_response_body(self, headers, request_method, response_code, max_chunk_size=None):
        raise NotImplementedError()
        yield "this is a generator"  # pragma: no cover

    def send_response_headers(self, response):
        raise NotImplementedError

    def send_response_body(self, response, chunks):
        raise NotImplementedError()


class Http1Layer(_StreamingHttpLayer):
    def __init__(self, ctx, mode):
        super(Http1Layer, self).__init__(ctx)
        self.mode = mode
        self.client_protocol = HTTP1Protocol(self.client_conn)
        self.server_protocol = HTTP1Protocol(self.server_conn)

    def read_request(self):
        return HTTPRequest.from_protocol(
            self.client_protocol,
            body_size_limit=self.config.body_size_limit
        )

    def send_request(self, request):
        self.server_conn.send(self.server_protocol.assemble(request))

    def read_response(self, request_method):
        return HTTPResponse.from_protocol(
            self.server_protocol,
            request_method=request_method,
            body_size_limit=self.config.body_size_limit,
            include_body=True
        )

    def send_response(self, response):
        self.client_conn.send(self.client_protocol.assemble(response))

    def read_response_headers(self):
        return HTTPResponse.from_protocol(
            self.server_protocol,
            request_method=None,  # does not matter if we don't read the body.
            body_size_limit=self.config.body_size_limit,
            include_body=False
        )

    def read_response_body(self, headers, request_method, response_code, max_chunk_size=None):
        return self.server_protocol.read_http_body_chunked(
            headers,
            self.config.body_size_limit,
            request_method,
            response_code,
            False,
            max_chunk_size
        )

    def send_response_headers(self, response):
        h = self.client_protocol._assemble_response_first_line(response)
        self.client_conn.wfile.write(h + "\r\n")
        h = self.client_protocol._assemble_response_headers(
            response,
            preserve_transfer_encoding=True
        )
        self.client_conn.send(h + "\r\n")

    def send_response_body(self, response, chunks):
        if self.client_protocol.has_chunked_encoding(response.headers):
            chunks = (
                "%d\r\n%s\r\n" % (len(chunk), chunk)
                for chunk in chunks
            )
        for chunk in chunks:
            self.client_conn.send(chunk)

    def check_close_connection(self, flow):
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

    def connect(self):
        self.ctx.connect()
        self.server_protocol = HTTP1Protocol(self.server_conn)

    def set_server(self, *args, **kwargs):
        self.ctx.set_server(*args, **kwargs)
        self.server_protocol = HTTP1Protocol(self.server_conn)

    def __call__(self):
        layer = HttpLayer(self, self.mode)
        layer()


# TODO: The HTTP2 layer is missing multiplexing, which requires a major rewrite.
class Http2Layer(_HttpLayer):
    def __init__(self, ctx, mode):
        super(Http2Layer, self).__init__(ctx)
        self.mode = mode
        self.client_protocol = HTTP2Protocol(self.client_conn, is_server=True,
                                             unhandled_frame_cb=self.handle_unexpected_frame_from_client)
        self.server_protocol = HTTP2Protocol(self.server_conn, is_server=False,
                                             unhandled_frame_cb=self.handle_unexpected_frame_from_server)

    def read_request(self):
        request = HTTPRequest.from_protocol(
            self.client_protocol,
            body_size_limit=self.config.body_size_limit
        )
        self._stream_id = request.stream_id
        return request

    def send_request(self, message):
        # TODO: implement flow control and WINDOW_UPDATE frames
        self.server_conn.send(self.server_protocol.assemble(message))

    def read_response(self, request_method):
        return HTTPResponse.from_protocol(
            self.server_protocol,
            request_method=request_method,
            body_size_limit=self.config.body_size_limit,
            include_body=True,
            stream_id=self._stream_id
        )

    def send_response(self, message):
        # TODO: implement flow control to prevent client buffer filling up
        # maintain a send buffer size, and read WindowUpdateFrames from client to increase the send buffer
        self.client_conn.send(self.client_protocol.assemble(message))

    def check_close_connection(self, flow):
        # TODO: add a timer to disconnect after a 10 second timeout
        return False

    def connect(self):
        self.ctx.connect()
        self.server_protocol = HTTP2Protocol(self.server_conn, is_server=False,
                                             unhandled_frame_cb=self.handle_unexpected_frame_from_server)
        self.server_protocol.perform_connection_preface()

    def set_server(self, *args, **kwargs):
        self.ctx.set_server(*args, **kwargs)
        self.server_protocol = HTTP2Protocol(self.server_conn, is_server=False,
                                             unhandled_frame_cb=self.handle_unexpected_frame_from_server)
        self.server_protocol.perform_connection_preface()

    def __call__(self):
        self.server_protocol.perform_connection_preface()
        layer = HttpLayer(self, self.mode)
        layer()

        # terminate the connection
        self.client_conn.send(GoAwayFrame().to_bytes())

    def handle_unexpected_frame_from_client(self, frame):
        if isinstance(frame, WindowUpdateFrame):
            # Clients are sending WindowUpdate frames depending on their flow control algorithm.
            # Since we cannot predict these frames, and we do not need to respond to them,
            # simply accept them, and hide them from the log.
            # Ideally we should keep track of our own flow control window and
            # stall transmission if the outgoing flow control buffer is full.
            return
        if isinstance(frame, PriorityFrame):
            # Clients are sending Priority frames depending on their implementation.
            # The RFC does not clearly state when or which priority preferences should be set.
            # Since we cannot predict these frames, and we do not need to respond to them,
            # simply accept them, and hide them from the log.
            # Ideally we should forward them to the server.
            return
        if isinstance(frame, GoAwayFrame):
            # Client wants to terminate the connection,
            # relay it to the server.
            self.server_conn.send(frame.to_bytes())
            return
        self.log("Unexpected HTTP2 frame from client: %s" % frame.human_readable(), "info")

    def handle_unexpected_frame_from_server(self, frame):
        if isinstance(frame, WindowUpdateFrame):
            # Servers are sending WindowUpdate frames depending on their flow control algorithm.
            # Since we cannot predict these frames, and we do not need to respond to them,
            # simply accept them, and hide them from the log.
            # Ideally we should keep track of our own flow control window and
            # stall transmission if the outgoing flow control buffer is full.
            return
        if isinstance(frame, GoAwayFrame):
            # Server wants to terminate the connection,
            # relay it to the client.
            self.client_conn.send(frame.to_bytes())
            return
        self.log("Unexpected HTTP2 frame from server: %s" % frame.human_readable(), "info")


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

    def __nonzero__(self):
        return bool(self.via)


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
        resp = self.read_response("CONNECT")
        if resp.code != 200:
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
        address = Address.wrap(address)
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
        self.__original_server_conn = None
        "Contains the original destination in transparent mode, which needs to be restored"
        "if an inline script modified the target server for a single http request"

    def __call__(self):
        if self.mode == "transparent":
            self.__original_server_conn = self.server_conn
        while True:
            try:
                flow = HTTPFlow(self.client_conn, self.server_conn, live=self)

                try:
                    request = self.read_request()
                except tcp.NetLibError:
                    # don't throw an error for disconnects that happen
                    # before/between requests.
                    return

                self.log("request", "debug", [repr(request)])

                # Handle Proxy Authentication
                self.authenticate(request)

                # Regular Proxy Mode: Handle CONNECT
                if self.mode == "regular" and request.form_in == "authority":
                    self.handle_regular_mode_connect(request)
                    return

                # Make sure that the incoming request matches our expectations
                self.validate_request(request)

                flow.request = request
                self.process_request_hook(flow)

                if not flow.response:
                    self.establish_server_connection(flow)
                    self.get_response_from_server(flow)

                self.send_response_to_client(flow)

                if self.check_close_connection(flow):
                    return

                # TODO: Implement HTTP Upgrade

                # Upstream Proxy Mode: Handle CONNECT
                if flow.request.form_in == "authority" and flow.response.code == 200:
                    self.handle_upstream_mode_connect(flow.request.copy())
                    return

            except (HttpErrorConnClosed, NetLibError, HttpError, ProtocolException) as e:
                if flow.request and not flow.response:
                    flow.error = Error(repr(e))
                    self.channel.ask("error", flow)
                try:
                    self.send_response(make_error_response(
                        getattr(e, "code", 502),
                        repr(e)
                    ))
                except NetLibError:
                    pass
                if isinstance(e, ProtocolException):
                    raise e
                else:
                    raise ProtocolException("Error in HTTP connection: %s" % repr(e), e)
            finally:
                flow.live = False

    def change_upstream_proxy_server(self, address):
        # Make set_upstream_proxy_server always available,
        # even if there's no UpstreamConnectLayer
        if address != self.server_conn.address:
            return self.set_server(address)

    def handle_regular_mode_connect(self, request):
        self.set_server((request.host, request.port))
        self.send_response(make_connect_response(request.httpversion))
        layer = self.ctx.next_layer(self)
        layer()

    def handle_upstream_mode_connect(self, connect_request):
        layer = UpstreamConnectLayer(self, connect_request)
        layer()

    def send_response_to_client(self, flow):
        if not (self.supports_streaming and flow.response.stream):
            # no streaming:
            # we already received the full response from the server and can
            # send it to the client straight away.
            self.send_response(flow.response)
        else:
            # streaming:
            # First send the headers and then transfer the response incrementally
            self.send_response_headers(flow.response)
            chunks = self.read_response_body(
                flow.response.headers,
                flow.request.method,
                flow.response.code,
                max_chunk_size=4096
            )
            if callable(flow.response.stream):
                chunks = flow.response.stream(chunks)
            self.send_response_body(flow.response, chunks)
            flow.response.timestamp_end = utils.timestamp()

    def get_response_from_server(self, flow):
        def get_response():
            self.send_request(flow.request)
            if self.supports_streaming:
                flow.response = self.read_response_headers()
            else:
                flow.response = self.read_response(flow.request.method)

        try:
            get_response()
        except (tcp.NetLibError, HttpErrorConnClosed) as v:
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

        if self.supports_streaming:
            if flow.response.stream:
                flow.response.content = CONTENT_MISSING
            else:
                flow.response.content = "".join(self.read_response_body(
                    flow.response.headers,
                    flow.request.method,
                    flow.response.code
                ))
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
        if response_reply == Kill:
            raise Kill()

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
            flow.request.host = self.__original_server_conn.address.host
            flow.request.port = self.__original_server_conn.address.port
            flow.request.scheme = "https" if self.__original_server_conn.tls_established else "http"

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
            if address != self.server_conn.address or tls != self.server_conn.ssl_established:
                self.set_server(address, tls, address.host)
            # Establish connection is neccessary.
            if not self.server_conn:
                self.connect()
        else:
            if not self.server_conn:
                self.connect()
            if tls:
                raise HttpException("Cannot change scheme in upstream proxy mode.")
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
        if request.form_in == "absolute" and request.scheme != "http":
            self.send_response(
                make_error_response(400, "Invalid request scheme: %s" % request.scheme))
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
            self.send_response(make_error_response(400, err_message))
            raise HttpException(err_message)

        if self.mode == "regular":
            request.form_out = "relative"

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
                raise InvalidCredentials("Proxy Authentication Required")
