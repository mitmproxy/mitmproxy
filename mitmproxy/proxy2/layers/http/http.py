import collections
import typing
from abc import ABC, abstractmethod

import h11
from h11._readers import ChunkedReader, ContentLengthReader, Http10Reader
from h11._receivebuffer import ReceiveBuffer

from mitmproxy import http
from mitmproxy.net.http import http1
from mitmproxy.net.http.http1 import read_sansio as http1_sansio
from mitmproxy.proxy.protocol.http import HTTPMode
from mitmproxy.proxy2 import commands, events
from mitmproxy.proxy2.context import Connection, Context, Server
from mitmproxy.proxy2.layer import Layer, NextLayer
from mitmproxy.proxy2.layers.tls import EstablishServerTLS, EstablishServerTLSReply
from mitmproxy.proxy2.utils import expect
from mitmproxy.utils import human

# FIXME: Combine HttpEvent and HttpCommand?

StreamIdentifier = int


class HttpEvent(events.Event):
    flow: http.HTTPFlow

    # we need flow identifiers on every event to avoid race conditions

    def __init__(self, flow: http.HTTPFlow):
        self.flow = flow

    def __repr__(self):
        x = self.__dict__.copy()
        x.pop("flow", None)
        return f"{type(self).__name__}({repr(x) if x else ''})"


class HttpCommand(commands.ConnectionCommand):
    pass


class OpenHttpConnection(HttpCommand):
    """
    Open a HTTP Connection. This may not actually open a connection, but return an existing HTTP connection instead.
    """
    blocking = True


class OpenHttpConnectionReply(events.CommandReply):
    command: OpenHttpConnection
    reply: typing.Optional[str]
    """error message"""


class SendHttp(HttpCommand):
    def __init__(self, event: HttpEvent, connection: Connection):
        super().__init__(connection)
        self.event = event

    def __repr__(self):
        return f"Send({self.event})"


HttpEventGenerator = typing.Iterator[HttpEvent]


# HttpCommandGenerator = typing.Generator[commands.Command, typing.Any, None]


class RequestHeaders(HttpEvent):
    pass


class ResponseHeaders(HttpEvent):
    pass


class RequestData(HttpEvent):
    data: bytes

    def __init__(self, data: bytes, flow: http.HTTPFlow):
        super().__init__(flow)
        self.data = data


class ResponseData(HttpEvent):
    data: bytes

    def __init__(self, data: bytes, flow: http.HTTPFlow):
        super().__init__(flow)
        self.data = data


class RequestEndOfMessage(HttpEvent):
    pass


class ResponseEndOfMessage(HttpEvent):
    pass


TBodyReader = typing.Union[ChunkedReader, Http10Reader, ContentLengthReader]


class Http1Connection(ABC):
    context: Context
    flow: http.HTTPFlow
    state: typing.Callable[[events.Event], HttpEventGenerator]
    body_reader: TBodyReader
    buf: ReceiveBuffer

    def __init__(self, context):
        self.context = context
        self.buf = ReceiveBuffer()

    def handle_event(self, event: events.Event) -> HttpEventGenerator:
        if isinstance(event, events.DataReceived):
            self.buf += event.data
        yield from self.state(event)

    @abstractmethod
    def send(self, event: HttpEvent) -> commands.TCommandGenerator:
        yield from ()

    def make_body_reader(self, expected_size: typing.Optional[int]) -> TBodyReader:
        if expected_size is None:
            return ChunkedReader()
        elif expected_size == -1:
            return Http10Reader()
        else:
            return ContentLengthReader(expected_size)

    def read_body(self, event: events.Event, is_request: bool) -> typing.Iterator[HttpEvent]:
        while True:
            try:
                if isinstance(event, events.DataReceived):
                    h11_event = self.body_reader(self.buf)
                elif isinstance(event, events.ConnectionClosed):
                    h11_event = self.body_reader.read_eof()
                else:
                    raise ValueError(f"Unexpected event: {event}")
            except h11.ProtocolError:
                raise  # FIXME

            if h11_event is None:
                return
            elif isinstance(h11_event, h11.Data):
                Data = RequestData if is_request else ResponseData
                yield Data(bytes(h11_event.data), self.flow)
            elif isinstance(h11_event, h11.EndOfMessage):
                EndOfMessage = RequestEndOfMessage if is_request else ResponseEndOfMessage
                yield EndOfMessage(self.flow)
                return

    def wait(self, event: events.Event) -> HttpEventGenerator:
        """
        We wait for the current flow to be finished before parsing the next message,
        as we may want to upgrade to WebSocket or plain TCP before that.
        """
        if isinstance(event, events.DataReceived):
            return
        elif isinstance(event, events.ConnectionClosed):
            return
        else:
            yield from ()
            raise ValueError(f"Unexpected event: {event}")


class Http1Server(Http1Connection):
    def __init__(self, context: Context):
        super().__init__(context)
        self.state = self.read_request_headers

    def send(self, event: HttpEvent) -> commands.TCommandGenerator:
        if isinstance(event, ResponseHeaders):
            raw = http1.assemble_response_head(event.flow.response)
            if self.flow.request.first_line_format == "authority":
                assert self.state == self.wait
                self.body_reader = self.make_body_reader(-1)
                self.state = self.read_request_body
                yield from self.state(events.DataReceived(self.context.client, b""))
        elif isinstance(event, ResponseData):
            if "chunked" in event.flow.response.headers.get("transfer-encoding", "").lower():
                raw = b"%x\r\n%s\r\n" % (len(event.data), event.data)
            else:
                raw = event.data
        elif isinstance(event, ResponseEndOfMessage):
            if "chunked" in event.flow.response.headers.get("transfer-encoding", "").lower():
                raw = b"0\r\n\r\n"
            else:
                raw = False
            assert self.state == self.wait
            self.state = self.read_request_headers
            yield from self.state(events.DataReceived(self.context.client, b""))
        else:
            raise NotImplementedError(f"{event}")

        if raw:
            yield commands.SendData(self.context.client, raw)

    def read_request_headers(self, event: events.Event) -> HttpEventGenerator:
        if isinstance(event, events.DataReceived):
            request_head = self.buf.maybe_extract_lines()
            if request_head:
                request_head = [bytes(x) for x in request_head]  # TODO: Make url.parse compatible with bytearrays
                request = http.HTTPRequest.wrap(http1_sansio.read_request_head(request_head))
                self.flow = http.HTTPFlow(
                    self.context.client,
                    self.context.server,
                )
                self.flow.request = request
                yield RequestHeaders(self.flow)

                if self.flow.request.first_line_format == "authority":
                    # The previous proxy server implementation tried to read the request body here:
                    # https://github.com/mitmproxy/mitmproxy/blob/45e3ae0f9cb50b0edbf4180fd969ea99d40bdf7b/mitmproxy/proxy/protocol/http.py#L251-L255
                    # We don't do this to be compliant with the h2 spec:
                    # https://http2.github.io/http2-spec/#CONNECT
                    self.state = self.wait
                else:
                    expected_size = http1.expected_http_body_size(self.flow.request)
                    self.body_reader = self.make_body_reader(expected_size)
                    self.state = self.read_request_body
                    yield from self.state(event)
        elif isinstance(event, events.ConnectionClosed):
            pass  # TODO: Better handling, tear everything down.
        else:
            raise ValueError(f"Unexpected event: {event}")

    def read_request_body(self, event: events.Event) -> HttpEventGenerator:
        for e in self.read_body(event, True):
            if isinstance(e, RequestEndOfMessage):
                self.state = self.wait
                yield from self.state(event)
            yield e


class Http1Client(Http1Connection):
    def __init__(self, context: Context):
        super().__init__(context)
        self.state = self.read_response_headers

    def send(self, event: HttpEvent) -> commands.TCommandGenerator:
        if isinstance(event, RequestHeaders):
            self.flow = event.flow
            raw = http1.assemble_request_head(event.flow.request)
        elif isinstance(event, RequestData):
            if "chunked" in event.flow.request.headers.get("transfer-encoding", "").lower():
                raw = b"%x\r\n%s\r\n" % (len(event.data), event.data)
            else:
                raw = event.data
        elif isinstance(event, RequestEndOfMessage):
            if "chunked" in event.flow.request.headers.get("transfer-encoding", "").lower():
                raw = b"0\r\n\r\n"
            else:
                raw = False
        else:
            raise NotImplementedError(f"{event}")

        if raw:
            yield commands.SendData(self.context.server, raw)

    def read_response_headers(self, event: events.ConnectionEvent) -> HttpEventGenerator:
        if isinstance(event, events.DataReceived):
            response_head = self.buf.maybe_extract_lines()

            if response_head:
                response_head = [bytes(x) for x in response_head]
                self.flow.response = http.HTTPResponse.wrap(http1_sansio.read_response_head(response_head))
                yield ResponseHeaders(self.flow)

                expected_size = http1.expected_http_body_size(self.flow.request, self.flow.response)
                self.body_reader = self.make_body_reader(expected_size)

                self.state = self.read_response_body
                yield from self.state(event)
        elif isinstance(event, events.ConnectionClosed):
            return  # TODO: Teardown?
        else:
            raise ValueError(f"Unexpected event: {event}")

    def read_response_body(self, event: events.ConnectionEvent) -> HttpEventGenerator:
        for e in self.read_body(event, False):
            if isinstance(e, ResponseEndOfMessage):
                self.state = self.read_response_headers
            yield e


class HttpStream(Layer):
    request_body_buf: bytes
    response_body_buf: bytes
    flow: http.HTTPFlow
    child_layer: typing.Optional[Layer] = None

    @property
    def mode(self):
        parent: HTTPLayer = self.context.layers[-2]
        return parent.mode

    def __init__(self, context: Context):
        super().__init__(context)
        self.request_body_buf = b""
        self.response_body_buf = b""
        self._handle_event = self.start

    @expect(events.Start)
    def start(self, event: events.Event) -> commands.TCommandGenerator:
        self._handle_event = self.read_request_headers
        yield from ()

    @expect(RequestHeaders)
    def read_request_headers(self, event: RequestHeaders) -> commands.TCommandGenerator:
        self.flow = event.flow
        if self.flow.request.first_line_format == "authority":
            yield from self.handle_connect()
            return
        else:
            yield commands.Hook("requestheaders", self.flow)

        if self.flow.request.headers.get("expect", "").lower() == "100-continue":
            raise NotImplementedError("expect nothing")
            # self.send_response(http.expect_continue_response)
            # request.headers.pop("expect")

        if self.flow.request.stream:
            raise NotImplementedError
        else:
            self._handle_event = self.read_request_body

    @expect(RequestData, RequestEndOfMessage)
    def read_request_body(self, event: events.Event) -> commands.TCommandGenerator:
        if isinstance(event, RequestData):
            self.request_body_buf += event.data
        elif isinstance(event, RequestEndOfMessage):
            self.flow.request.data.content = self.request_body_buf
            self.request_body_buf = b""
            yield from self.handle_request()

    def handle_connect(self) -> commands.TCommandGenerator:
        yield commands.Hook("http_connect", self.flow)

        self.context.server.address = (self.flow.request.host, self.flow.request.port)
        if self.context.options.connection_strategy == "eager":
            err = yield commands.OpenConnection(self.context.server)
            if err:
                self.flow.response = http.HTTPResponse.make(
                    502, f"Cannot connect to {human.format_address(self.context.server.address)}: {err}"
                )
        else:
            raise NotImplementedError("<insert lazy joke here>")

        if not self.flow.response:
            self.flow.response = http.make_connect_response(self.flow.request.data.http_version)

        yield SendHttp(ResponseHeaders(self.flow), self.context.client)

        if 200 <= self.flow.response.status_code < 300:
            self.child_layer = NextLayer(self.context)
            yield from self.child_layer.handle_event(events.Start())
            self._handle_event = self.passthrough
        else:
            yield SendHttp(ResponseData(self.flow.response.data.content, self.flow), self.context.client)
            yield SendHttp(ResponseEndOfMessage(self.flow), self.context.client)

    @expect(RequestData, RequestEndOfMessage, events.Event)
    def passthrough(self, event: events.Event) -> commands.TCommandGenerator:
        # HTTP events -> normal connection events
        if isinstance(event, RequestData):
            event = events.DataReceived(self.context.client, event.data)
        elif isinstance(event, RequestEndOfMessage):
            event = events.ConnectionClosed(self.context.client)

        for command in self.child_layer.handle_event(event):
            # normal connection events -> HTTP events
            if isinstance(command, commands.SendData) and command.connection == self.context.client:
                yield SendHttp(ResponseData(command.data, self.flow), self.context.client)
            elif isinstance(command, commands.CloseConnection) and command.connection == self.context.client:
                yield SendHttp(ResponseEndOfMessage(self.flow), self.context.client)
            elif isinstance(command, commands.OpenConnection) and command.connection == self.context.server:
                yield from self.passthrough(events.OpenConnectionReply(command, None))
            else:
                yield command

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
            # FIXME wrong location
            self.context.server.address = (self.flow.request.host, self.flow.request.port)
            err = yield OpenHttpConnection(self.context.server)
            if err:
                raise NotImplementedError
            yield SendHttp(RequestHeaders(self.flow), self.context.server)

            if self.flow.request.stream:
                raise NotImplementedError
            else:
                yield SendHttp(RequestData(self.flow.request.data.content, self.flow), self.context.server)
                yield SendHttp(RequestEndOfMessage(self.flow), self.context.server)
            self._handle_event = self.read_response_headers

    @expect(ResponseHeaders)
    def read_response_headers(self, event: events.Event) -> commands.TCommandGenerator:
        yield commands.Hook("responseheaders", self.flow)
        if not self.flow.response.stream:
            self._handle_event = self.read_response_body
        else:
            raise NotImplementedError

    @expect(ResponseData, ResponseEndOfMessage)
    def read_response_body(self, event: events.Event) -> commands.TCommandGenerator:
        if isinstance(event, ResponseData):
            self.response_body_buf += event.data
        elif isinstance(event, ResponseEndOfMessage):
            self.flow.response.data.content = self.response_body_buf
            self.response_body_buf = b""
            yield from self.handle_response()

    def handle_response(self):
        yield commands.Hook("response", self.flow)
        yield SendHttp(ResponseHeaders(self.flow), self.context.client)

        if self.flow.response.stream:
            raise NotImplementedError
        else:
            yield SendHttp(ResponseData(self.flow.response.data.content, self.flow), self.context.client)
            yield SendHttp(ResponseEndOfMessage(self.flow), self.context.client)


class HTTPLayer(Layer):
    """
    ConnectionEvent: We have received b"GET /\r\n\r\n" from the client.
    HttpEvent: We have received request headers
    HttpCommand: Send request headers to X
    ConnectionCommand: Send b"GET /\r\n\r\n" to server.

    ConnectionEvent -> HttpEvent -> HttpCommand -> ConnectionCommand
    """
    mode: HTTPMode
    stream_by_command: typing.Dict[commands.Command, HttpStream]
    streams: typing.Dict[int, HttpStream]
    connections: typing.Dict[Connection, typing.Union[Http1Connection, HttpStream]]
    waiting_for_connection: typing.DefaultDict[Connection, typing.List[OpenHttpConnection]]
    event_queue: typing.Deque[
        typing.Union[HttpEvent, HttpCommand, commands.Command]
    ]

    def __init__(self, context: Context, mode: HTTPMode):
        super().__init__(context)
        self.mode = mode

        self.connections = {
            context.client: Http1Server(context)
        }
        self.waiting_for_connection = collections.defaultdict(list)
        self.streams = {}
        self.stream_by_command = {}
        self.event_queue = collections.deque()

    def __repr__(self):
        return f"HTTPLayer(conns: {len(self.connections)}, events: {[type(e).__name__ for e in self.event_queue]})"

    def _handle_event(self, event: events.Event):
        if isinstance(event, events.Start):
            return
        elif isinstance(event, events.OpenConnectionReply) and event.command.connection in self.waiting_for_connection:
            if event.command.connection.tls:
                new_command = EstablishServerTLS(event.command.connection)
                new_command.blocking = object()
                yield new_command
            else:
                self.make_http_connection(event.command.connection)
        elif isinstance(event, EstablishServerTLSReply) and event.command.connection in self.waiting_for_connection:
            self.make_http_connection(event.command.connection)
        elif isinstance(event, events.CommandReply):
            try:
                stream = self.stream_by_command.pop(event.command)
            except KeyError:
                raise
            if isinstance(event, events.OpenConnectionReply):
                self.connections[event.command.connection] = stream
            self.event_to_stream(stream, event)
        elif isinstance(event, events.ConnectionEvent):
            handler = self.connections[event.connection]
            self.event_to_stream(handler, event)
        else:
            raise ValueError(f"Unexpected event: {event}")

        while self.event_queue:
            event = self.event_queue.popleft()
            if isinstance(event, RequestHeaders):
                self.streams[event.flow.id] = self.make_stream()
            if isinstance(event, HttpEvent):
                stream = self.streams[event.flow.id]
                self.event_to_stream(stream, event)
            elif isinstance(event, SendHttp):
                conn = self.connections[event.connection]
                evts = conn.send(event.event)
                self.event_queue.extend(evts)
            elif isinstance(event, OpenHttpConnection):
                if event.connection in self.connections:
                    stream = self.stream_by_command.pop(event)
                    self.event_to_stream(stream, OpenHttpConnectionReply(event, None))
                else:
                    if event.connection not in self.waiting_for_connection:
                        open_command = commands.OpenConnection(event.connection)
                        open_command.blocking = object()
                        self.event_queue.append(open_command)
                    self.waiting_for_connection[event.connection].append(event)
            elif isinstance(event, commands.Command):
                yield event
            else:
                raise ValueError(f"Unexpected event: {event}")

    def make_stream(self) -> HttpStream:
        ctx = Context(
            self.context.client,
            self.context.options
        )
        ctx.server = self.context.server
        ctx.layers = self.context.layers.copy()

        stream = HttpStream(ctx)
        if self.debug:
            stream.debug = self.debug + "  "
        self.event_to_stream(stream, events.Start())
        return stream

    def make_http_connection(self, connection: Server):
        if connection.tls_established and connection.alpn == b"h2":
            raise NotImplementedError
        else:
            self.connections[connection] = Http1Client(self.context)

        waiting = self.waiting_for_connection.pop(connection)
        for cmd in waiting:
            stream = self.stream_by_command.pop(cmd)
            self.event_to_stream(stream, OpenHttpConnectionReply(cmd, None))  # TODO: Error handling.

    def event_to_stream(
            self,
            stream: HttpStream,
            event: events.Event,
    ) -> None:
        stream_events = list(stream.handle_event(event))
        for se in stream_events:
            # Streams may yield blocking commands, which ultimately generate CommandReply events.
            # Those need to be routed back to the correct stream, so we need to keep track of that.
            if isinstance(se, commands.Command) and se.blocking:
                self.stream_by_command[se] = stream

        self.event_queue.extend(stream_events)
