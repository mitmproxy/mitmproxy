import typing
from warnings import warn

import h11
from h11._readers import ChunkedReader, ContentLengthReader, Http10Reader
from h11._receivebuffer import ReceiveBuffer

from mitmproxy import http
from mitmproxy.net.http import http1
from mitmproxy.net.http.http1 import read_sansio as http1_sansio
from mitmproxy.proxy.protocol.http import HTTPMode
from mitmproxy.proxy2 import commands, events
from mitmproxy.proxy2.context import Context
from mitmproxy.proxy2.layer import Layer
from mitmproxy.proxy2.utils import expect


class ClientHTTP1Layer(Layer):
    mode: HTTPMode
    flow: typing.Optional[http.HTTPFlow]
    client_buf: ReceiveBuffer
    body_reader: typing.Union[ChunkedReader, Http10Reader, ContentLengthReader]
    body_buf: bytes

    # this is like a mini state machine.
    state: typing.Callable[[events.Event], commands.TCommandGenerator]

    def __init__(self, context: Context, mode: HTTPMode):
        super().__init__(context)
        self.mode = mode

        self.client_buf = ReceiveBuffer()
        self.body_buf = b""

        self.state = self.read_request_headers

    @expect(events.Start, events.DataReceived, events.ConnectionClosed)
    def _handle_event(self, event: events.Event) -> commands.TCommandGenerator:
        if isinstance(event, events.Start):
            return
        elif isinstance(event, events.DataReceived) and event.connection == self.context.client:
            self.client_buf += event.data
        else:
            return warn(f"ClientHTTP1Layer unimplemented: {event}")

        yield from self.state(event)

    def read_request_headers(self, event: events.Event) -> commands.TCommandGenerator:
        if isinstance(event, events.DataReceived) and event.connection == self.context.client:
            request_head = self.client_buf.maybe_extract_lines()
            if request_head:
                self.flow = http.HTTPFlow(
                    self.context.client,
                    self.context.server,
                )
                self.flow.request = http.HTTPRequest.wrap(http1_sansio.read_request_head(request_head))

                if self.flow.request.first_line_format != "authority":
                    yield commands.Hook("requestheaders", self.flow)

                if self.flow.request.headers.get("expect", "").lower() == "100-continue":
                    raise NotImplementedError()
                    # self.send_response(http.expect_continue_response)
                    # request.headers.pop("expect")

                expected_size = http1.expected_http_body_size(self.flow.request)
                if expected_size is None:
                    self.body_reader = ChunkedReader()
                elif expected_size == -1:
                    self.body_reader = Http10Reader()
                else:
                    self.body_reader = ContentLengthReader(expected_size)

                if not self.flow.request.stream:
                    yield from self.start_read_request_body()
                else:
                    yield from self.request_received()
        else:
            return warn(f"ClientHTTP1Layer.read_request_headers: unimplemented {event}")

    def start_read_request_body(self) -> commands.TCommandGenerator:
        self.state = self.read_request_body
        yield from self.read_request_body(events.DataReceived(self.context.client, b""))

    def read_request_body(self, event: events.Event) -> commands.TCommandGenerator:
        if isinstance(event, events.DataReceived) and event.connection == self.context.client:
            try:
                event = self.body_reader(self.client_buf)
            except h11.ProtocolError as e:
                raise  # FIXME
        elif isinstance(event, events.ConnectionClosed):
            try:
                event = self.body_reader.read_eof()
            except h11.ProtocolError as e:
                raise  # FIXME
        else:
            return warn(f"ClientHTTP1Layer.read_request_body: unimplemented {event}")

        if event is None:
            return
        elif isinstance(event, h11.Data):
            self.body_buf += event.data
        elif isinstance(event, h11.EndOfMessage):
            self.flow.request.data.content = self.body_buf
            self.body_buf = b""
            yield from self.request_received()

    def request_received(self) -> commands.TCommandGenerator:
        # set first line format to relative in regular mode,
        # see https://github.com/mitmproxy/mitmproxy/issues/1759
        if self.mode is HTTPMode.regular and self.flow.request.first_line_format == "absolute":
            self.flow.request.first_line_format = "relative"

        # update host header in reverse proxy mode
        if self.context.options.mode.startswith("reverse:") and not self.context.options.keep_host_header:
            self.flow.request.host_header = self.context.server.address[0]

        # Determine .scheme, .host and .port attributes for inline scripts. For
        # absolute-form requests, they are directly given in the request. For
        # authority-form requests, we only need to determine the request
        # scheme. For relative-form requests, we need to determine host and
        # port as well.
        if self.mode is HTTPMode.transparent:
            # Setting request.host also updates the host header, which we want
            # to preserve
            host_header = self.flow.request.host_header
            self.flow.request.host = self.context.server.address[0]
            self.flow.request.port = self.context.server.address[1]
            self.flow.request.host_header = host_header  # set again as .host overwrites this.
            self.flow.request.scheme = "https" if self.context.server.tls else "http"
        yield commands.Hook("request", self.flow)

        if self.flow.response:
            # response was set by an inline script.
            # we now need to emulate the responseheaders hook.
            yield commands.Hook("responseheaders", self.flow)
            yield from self.response_received()
        else:
            raise NotImplementedError("Get your responses elsewhere.")

    def response_received(self):
        yield commands.Hook("response", self.flow)

        raw = http1.assemble_response_head(self.flow.response)
        yield commands.SendData(self.context.server, raw)

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
            # Handle a successful HTTP 101 Switching Protocols Response,
            # received after e.g. a WebSocket upgrade request.
            # Check for WebSocket handshake
            is_websocket = (
                    websockets.check_handshake(f.request.headers) and
                    websockets.check_handshake(f.response.headers)
            )
            if is_websocket and not self.config.options.websocket:
                self.log(
                    "Client requested WebSocket connection, but the protocol is disabled.",
                    "info"
                )

            if is_websocket and self.config.options.websocket:
                layer = WebSocketLayer(self, f)
            else:
                layer = self.ctx.next_layer(self)
            layer()
            return False  # should never be reached