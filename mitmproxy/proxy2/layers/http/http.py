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
from mitmproxy.proxy2.context import Connection, Context
from mitmproxy.proxy2.layer import Layer
from mitmproxy.proxy2.utils import expect


class HttpEvent(events.Event):
    stream_id: int

    def __init__(self, stream_id: int):
        self.stream_id = stream_id


class HttpCommand(commands.Command):
    connection: Connection

    def __init__(self, connection):
        self.connection = connection


HttpEventGenerator = typing.Generator[HttpEvent, typing.Any, None]
HttpCommandGenerator = typing.Generator[commands.Command, typing.Any, None]


class RequestHeaders(HttpEvent):
    request: http.HTTPRequest

    def __init__(self, stream_id: int, request):
        super().__init__(stream_id)
        self.request = request


class ResponseHeaders(HttpCommand):
    request: http.HTTPResponse

    def __init__(self, connection: Connection, response):
        super().__init__(connection)
        self.response = response


class EndOfMessage(HttpEvent):
    pass


class Data(HttpEvent):
    data: bytes

    def __init__(self, stream_id: int, data: bytes):
        super().__init__(stream_id)
        self.data = data


class Http1Client:
    # this is like a mini state machine.
    stream_id = 1
    state: typing.Callable[[events.Event], commands.TCommandGenerator]
    body_reader: typing.Union[ChunkedReader, Http10Reader, ContentLengthReader]
    buf: ReceiveBuffer
    context: Context

    def __init__(self, context):
        self.context = context
        self.state = self.read_request_headers
        self.buf = ReceiveBuffer()

    def receive_connection_event(self, event: events.ConnectionEvent) -> HttpEventGenerator:
        if isinstance(event, events.DataReceived):
            self.buf += event.data
        yield from self.state(event)

    def receive_http_command(self, command: HttpCommand) -> commands.TCommandGenerator:
        if isinstance(command, ResponseHeaders):
            raw = http1.assemble_response_head(command.response)
            yield commands.SendData(self.context.client, raw)
        else:
            raise NotImplementedError(f"{command}")

    def read_request_headers(self, event: events.ConnectionEvent):
        if isinstance(event, events.DataReceived):
            request_head = self.buf.maybe_extract_lines()
            # TODO: Make url.parse compatible with bytearrays
            request_head = [bytes(x) for x in request_head]
            if request_head:
                request = http.HTTPRequest.wrap(http1_sansio.read_request_head(request_head))
                yield RequestHeaders(self.stream_id, request)

                expected_size = http1.expected_http_body_size(request)
                if expected_size is None:
                    self.body_reader = ChunkedReader()
                elif expected_size == -1:
                    self.body_reader = Http10Reader()
                else:
                    self.body_reader = ContentLengthReader(expected_size)
                self.state = self.read_request_body
                yield from self.state(event)
        else:
            return warn(f"Http1Client.read_request_headers: unimplemented {event}")

    def read_request_body(self, event: events.ConnectionEvent):

        if isinstance(event, events.DataReceived):
            try:
                event = self.body_reader(self.buf)
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
            yield Data(self.stream_id, event.data)
        elif isinstance(event, h11.EndOfMessage):
            yield EndOfMessage(self.stream_id)
            # FIXME: Check for abort here or somewhere else?
            self.stream_id += 2
            self.state = self.read_request_headers


class HttpStream(Layer):
    request_body_buf: bytes
    stream_id: int

    @property
    def mode(self):
        parent: HTTPLayer = self.context.layers[-2]
        return parent.mode

    def __init__(self, context: Context, stream_id: int):
        super().__init__(context)
        self.stream_id = stream_id
        self.request_body_buf = b""
        self._handle_event = self.start

    @expect(events.Start)
    def start(self, event: events.Event) -> commands.TCommandGenerator:
        self._handle_event = self.read_request_headers
        yield from ()

    def read_request_headers(self, event: events.Event) -> commands.TCommandGenerator:
        if isinstance(event, RequestHeaders):
            self.flow = http.HTTPFlow(
                self.context.client,
                self.context.server,
            )
            self.flow.request = event.request
            if self.flow.request.first_line_format == "authority":
                raise NotImplementedError("authority")
            else:
                yield commands.Hook("requestheaders", self.flow)

            if self.flow.request.headers.get("expect", "").lower() == "100-continue":
                raise NotImplementedError("expect nothing")
                # self.send_response(http.expect_continue_response)
                # request.headers.pop("expect")

            if not self.flow.request.stream:
                self._handle_event = self.read_request_body
            else:
                raise NotImplementedError

    def read_request_body(self, event: events.Event) -> commands.TCommandGenerator:
        if isinstance(event, Data):
            self.request_body_buf += event.data
        elif isinstance(event, EndOfMessage):
            self.flow.request.data.content = self.request_body_buf
            self.request_body_buf = b""
            yield from self.handle_request()

    def handle_request(self) -> commands.TCommandGenerator:
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
            # FIXME
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
            yield from self.handle_response()
        else:
            raise NotImplementedError("Get your responses elsewhere.")

    def handle_response(self):
        yield commands.Hook("response", self.flow)
        yield ResponseHeaders(self.context.client, self.flow.response)


class HTTPLayer(Layer):
    """
    ConnectionEvent: We have received b"GET /\r\n\r\n" from the client.
    HttpEvent: We have received request headers
    HttpCommand: Send request headers to X
    Connection Command: Send b"GET /\r\n\r\n" to server.

    ConnectionEvent -> HttpEvent -> HttpCommand -> ConnectionCommand
    """
    mode: HTTPMode
    flow: typing.Optional[http.HTTPFlow]
    client_layer: Layer
    stream_by_command: typing.Dict[commands.Command, HttpStream]
    streams: typing.Dict[int, HttpStream]
    connections: typing.Dict[Connection, Http1Client]

    def __init__(self, context: Context, mode: HTTPMode):
        super().__init__(context)
        self.mode = mode

        self.connections = {
            context.client: Http1Client(context)
        }
        self.streams = {}
        self.stream_by_command = {}

    def _handle_event(self, event: events.Event):
        if isinstance(event, events.Start):
            return
        elif isinstance(event, events.CommandReply):
            stream = self.stream_by_command.pop(event.command)
            # FIXME: Should initiate connection object here.
            yield from self.event_to_stream(stream, event)
        elif isinstance(event, events.ConnectionEvent):
            http_events = self.connections[event.connection].receive_connection_event(event)
            for event in http_events:
                if isinstance(event, RequestHeaders):
                    self.streams[event.stream_id] = HttpStream(self.context, event.stream_id)
                    yield from self.event_to_stream(self.streams[event.stream_id], events.Start())
                yield from self.event_to_stream(self.streams[event.stream_id], event)
        else:
            return warn(f"HTTPLayer._handle_event: unimplemented {event}")

    def event_to_stream(self, stream: Layer, event: events.Event):
        for command in stream.handle_event(event):
            if isinstance(command, HttpCommand):
                yield from self.connections[command.connection].receive_http_command(command)
            else:
                if command.blocking:
                    self.stream_by_command[command] = stream
                yield command
