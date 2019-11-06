import collections
import typing
from abc import ABC, abstractmethod

import h11
from h11._readers import ChunkedReader, ContentLengthReader, Http10Reader
from h11._receivebuffer import ReceiveBuffer

from mitmproxy import flow, http
from mitmproxy.net.http import http1
from mitmproxy.net.http.http1 import read_sansio as http1_sansio
from mitmproxy.proxy.protocol.http import HTTPMode
from mitmproxy.proxy2 import commands, events
from mitmproxy.proxy2.context import Client, Connection, Context, Server
from mitmproxy.proxy2.layer import Layer, NextLayer
from mitmproxy.proxy2.layers.tls import EstablishServerTLS, EstablishServerTLSReply
from mitmproxy.proxy2.utils import expect
from mitmproxy.utils import human

StreamId = int


class HttpEvent(events.Event):
    stream_id: StreamId

    # we need stream ids on every event to avoid race conditions

    def __init__(self, stream_id: StreamId):
        self.stream_id = stream_id

    def __repr__(self) -> str:
        x = self.__dict__.copy()
        x.pop("stream_id")
        return f"{type(self).__name__}({repr(x) if x else ''})"


class HttpCommand(commands.Command):
    pass


class GetHttpConnection(HttpCommand):
    """
    Open a HTTP Connection. This may not actually open a connection, but return an existing HTTP connection instead.
    """
    blocking = True
    address: typing.Tuple[str, int]
    tls: bool

    def __init__(self, address: typing.Tuple[str, int], tls: bool):
        self.address = address
        self.tls = tls

    def connection_spec_matches(self, connection: Connection) -> bool:
        return (
                self.address == connection.address
                and
                self.tls == connection.tls
        )


class GetHttpConnectionReply(events.CommandReply):
    command: GetHttpConnection
    reply: typing.Optional[str]
    """error message"""


class SendHttp(HttpCommand):
    connection: Connection
    event: HttpEvent

    def __init__(self, event: HttpEvent, connection: Connection):
        self.connection = connection
        self.event = event

    def __repr__(self) -> str:
        return f"Send({self.event})"


HttpEventGenerator = typing.Iterator[HttpEvent]


class RequestHeaders(HttpEvent):
    request: http.HTTPRequest

    def __init__(self, request: http.HTTPRequest, stream_id: StreamId):
        super().__init__(stream_id)
        self.request = request


class ResponseHeaders(HttpEvent):
    response: http.HTTPResponse

    def __init__(self, response: http.HTTPResponse, stream_id: StreamId):
        super().__init__(stream_id)
        self.response = response


class RequestData(HttpEvent):
    data: bytes

    def __init__(self, data: bytes, stream_id: StreamId):
        super().__init__(stream_id)
        self.data = data


class ResponseData(HttpEvent):
    data: bytes

    def __init__(self, data: bytes, stream_id: StreamId):
        super().__init__(stream_id)
        self.data = data


class RequestEndOfMessage(HttpEvent):
    pass


class ResponseEndOfMessage(HttpEvent):
    pass


TBodyReader = typing.Union[ChunkedReader, Http10Reader, ContentLengthReader]


class Http1Connection(ABC):
    conn: Connection
    stream_id: StreamId = None
    request: http.HTTPRequest
    response: http.HTTPResponse
    state: typing.Callable[[events.Event], HttpEventGenerator]
    body_reader: TBodyReader
    buf: ReceiveBuffer

    def __init__(self, conn: Connection):
        assert isinstance(conn, Connection)
        self.conn = conn
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
                h11_event.data: bytearray  # type checking
                if is_request:
                    yield RequestData(bytes(h11_event.data), self.stream_id)
                else:
                    yield ResponseData(bytes(h11_event.data), self.stream_id)
            elif isinstance(h11_event, h11.EndOfMessage):
                if is_request:
                    yield RequestEndOfMessage(self.stream_id)
                else:
                    yield ResponseEndOfMessage(self.stream_id)
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
    """A simple HTTP/1 server with no pipelining support."""
    conn: Client

    def __init__(self, conn: Client):
        super().__init__(conn)
        self.state = self.read_request_headers
        self.stream_id = -1

    def send(self, event: HttpEvent) -> commands.TCommandGenerator:
        if isinstance(event, ResponseHeaders):
            self.response = event.response
            raw = http1.assemble_response_head(event.response)
            if self.request.first_line_format == "authority":
                assert self.state == self.wait
                self.body_reader = self.make_body_reader(-1)
                self.state = self.read_request_body
                yield from self.state(events.DataReceived(self.conn, b""))
        elif isinstance(event, ResponseData):
            if "chunked" in self.response.headers.get("transfer-encoding", "").lower():
                raw = b"%x\r\n%s\r\n" % (len(event.data), event.data)
            else:
                raw = event.data
        elif isinstance(event, ResponseEndOfMessage):
            if "chunked" in self.response.headers.get("transfer-encoding", "").lower():
                raw = b"0\r\n\r\n"
            elif http1.expected_http_body_size(self.request, self.response) == -1:
                yield commands.CloseConnection(self.conn)
                return
            else:
                raw = False
            self.request = None
            self.response = None
            self.stream_id += 2
            self.state = self.read_request_headers
            yield from self.state(events.DataReceived(self.conn, b""))
        else:
            raise NotImplementedError(f"{event}")

        if raw:
            yield commands.SendData(self.conn, raw)

    def read_request_headers(self, event: events.Event) -> HttpEventGenerator:
        if isinstance(event, events.DataReceived):
            request_head = self.buf.maybe_extract_lines()
            if request_head:
                request_head = [bytes(x) for x in request_head]  # TODO: Make url.parse compatible with bytearrays
                self.request = http.HTTPRequest.wrap(http1_sansio.read_request_head(request_head))
                yield RequestHeaders(self.request, self.stream_id)

                if self.request.first_line_format == "authority":
                    # The previous proxy server implementation tried to read the request body here:
                    # https://github.com/mitmproxy/mitmproxy/blob/45e3ae0f9cb50b0edbf4180fd969ea99d40bdf7b/mitmproxy/proxy/protocol/http.py#L251-L255
                    # We don't do this to be compliant with the h2 spec:
                    # https://http2.github.io/http2-spec/#CONNECT
                    self.state = self.wait
                else:
                    expected_size = http1.expected_http_body_size(self.request)
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
    conn: Server
    send_queue: typing.List[HttpEvent]
    """A queue of send events for flows other than the one that is currently being transmitted."""

    def __init__(self, conn: Server):
        super().__init__(conn)
        self.state = self.read_response_headers
        self.send_queue = []

    def send(self, event: HttpEvent) -> commands.TCommandGenerator:
        if not self.stream_id:
            assert isinstance(event, RequestHeaders)
            self.stream_id = event.stream_id
            self.request = event.request
        if self.stream_id != event.stream_id:
            # Assuming an h2 server, we may have multiple Streams that try to send requests
            # over a single h1 connection. To keep things relatively simple, we don't do any HTTP/1 pipelining
            # but keep a queue of still-to-send requests.
            self.send_queue.append(event)
            return

        if isinstance(event, RequestHeaders):
            raw = http1.assemble_request_head(event.request)
        elif isinstance(event, RequestData):
            if "chunked" in self.request.headers.get("transfer-encoding", "").lower():
                raw = b"%x\r\n%s\r\n" % (len(event.data), event.data)
            else:
                raw = event.data
        elif isinstance(event, RequestEndOfMessage):
            if "chunked" in self.request.headers.get("transfer-encoding", "").lower():
                raw = b"0\r\n\r\n"
            elif http1.expected_http_body_size(self.request) == -1:
                assert not self.send_queue
                yield commands.CloseConnection(self.conn)
                return
            else:
                raw = False
        else:
            raise NotImplementedError(f"{event}")

        if raw:
            yield commands.SendData(self.conn, raw)

    def read_response_headers(self, event: events.ConnectionEvent) -> HttpEventGenerator:
        if isinstance(event, events.DataReceived):
            response_head = self.buf.maybe_extract_lines()

            if response_head:
                response_head = [bytes(x) for x in response_head]
                self.response = http.HTTPResponse.wrap(http1_sansio.read_response_head(response_head))
                yield ResponseHeaders(self.response, self.stream_id)

                expected_size = http1.expected_http_body_size(self.request, self.response)
                self.body_reader = self.make_body_reader(expected_size)

                self.state = self.read_response_body
                yield from self.state(event)
        elif isinstance(event, events.ConnectionClosed):
            if self.stream_id:
                raise NotImplementedError(f"{event}")
            else:
                return
        else:
            raise ValueError(f"Unexpected event: {event}")

    def read_response_body(self, event: events.ConnectionEvent) -> HttpEventGenerator:
        for e in self.read_body(event, False):
            yield e
            if isinstance(e, ResponseEndOfMessage):
                self.state = self.read_response_headers
                self.stream_id = None
                self.request = None
                self.response = None
                if self.send_queue:
                    events = self.send_queue
                    self.send_queue = []
                    for e in events:
                        yield from self.send(e)


class Http2Server:
    pass  # TODO


class Http2Client:
    pass  # TODO


class HttpStream(Layer):
    request_body_buf: bytes
    response_body_buf: bytes
    flow: http.HTTPFlow
    stream_id: StreamId
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
        self.stream_id = event.stream_id
        self.flow = http.HTTPFlow(
            self.context.client,
            self.context.server
        )
        self.flow.request = event.request

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
            raise NotImplementedError  # FIXME
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

        self.context.server = Server((self.flow.request.host, self.flow.request.port))
        if self.context.options.connection_strategy == "eager":
            err = yield commands.OpenConnection(self.context.server)
            if err:
                self.flow.response = http.HTTPResponse.make(
                    502, f"Cannot connect to {human.format_address(self.context.server.address)}: {err}"
                )

        if not self.flow.response:
            self.flow.response = http.make_connect_response(self.flow.request.data.http_version)

        yield SendHttp(ResponseHeaders(self.flow.response, self.stream_id), self.context.client)

        if 200 <= self.flow.response.status_code < 300:
            self.child_layer = NextLayer(self.context)
            yield from self.child_layer.handle_event(events.Start())
            self._handle_event = self.passthrough
        else:
            yield SendHttp(ResponseData(self.flow.response.data.content, self.stream_id), self.context.client)
            yield SendHttp(ResponseEndOfMessage(self.stream_id), self.context.client)

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
                yield SendHttp(ResponseData(command.data, self.stream_id), self.context.client)
            elif isinstance(command, commands.CloseConnection) and command.connection == self.context.client:
                yield SendHttp(ResponseEndOfMessage(self.stream_id), self.context.client)
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
            connection, err = yield GetHttpConnection(
                (self.flow.request.host, self.flow.request.port),
                self.flow.request.scheme == "https"
            )
            if err:
                yield from self.send_error_response(502, err)
                self.flow.error = flow.Error(err)
                yield commands.Hook("error", self.flow)
                return

            yield SendHttp(RequestHeaders(self.flow.request, self.stream_id), connection)

            if self.flow.request.stream:
                raise NotImplementedError
            else:
                yield SendHttp(RequestData(self.flow.request.data.content, self.stream_id), connection)
                yield SendHttp(RequestEndOfMessage(self.stream_id), connection)
            self._handle_event = self.read_response_headers

    @expect(ResponseHeaders)
    def read_response_headers(self, event: ResponseHeaders) -> commands.TCommandGenerator:
        self.flow.response = event.response
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
        yield SendHttp(ResponseHeaders(self.flow.response, self.stream_id), self.context.client)

        if self.flow.response.stream:
            raise NotImplementedError
        else:
            yield SendHttp(ResponseData(self.flow.response.data.content, self.stream_id), self.context.client)
            yield SendHttp(ResponseEndOfMessage(self.stream_id), self.context.client)

    def send_error_response(self, status_code: int, message: str, headers=None):
        response = http.make_error_response(status_code, message, headers)
        yield SendHttp(ResponseHeaders(response, self.stream_id), self.context.client)
        yield SendHttp(ResponseData(response.data.content, self.stream_id), self.context.client)
        yield SendHttp(ResponseEndOfMessage(self.stream_id), self.context.client)


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
    waiting_for_connection: typing.DefaultDict[Connection, typing.List[GetHttpConnection]]
    event_queue: typing.Deque[
        typing.Union[HttpEvent, HttpCommand, commands.Command]
    ]

    def __init__(self, context: Context, mode: HTTPMode):
        super().__init__(context)
        self.mode = mode

        self.waiting_for_connection = collections.defaultdict(list)
        self.streams = {}
        self.stream_by_command = {}
        self.event_queue = collections.deque()

        self.connections = {
            context.client: Http1Server(context.client)
        }
        if self.context.server.connected:
            self.make_http_connection(self.context.server)

    def __repr__(self):
        return f"HTTPLayer(conns: {len(self.connections)}, events: {[type(e).__name__ for e in self.event_queue]})"

    def _handle_event(self, event: events.Event):
        if isinstance(event, events.Start):
            return
        elif isinstance(event, (EstablishServerTLSReply, events.OpenConnectionReply)) and \
                event.command.connection in self.waiting_for_connection:
            if event.reply:
                waiting = self.waiting_for_connection.pop(event.command.connection)
                for cmd in waiting:
                    stream = self.stream_by_command.pop(cmd)
                    self.event_to_child(stream, GetHttpConnectionReply(cmd, (None, event.reply)))
            else:
                yield from self.make_http_connection(event.command.connection)
        elif isinstance(event, EstablishServerTLSReply) and event.command.connection in self.waiting_for_connection:
            yield from self.make_http_connection(event.command.connection)
        elif isinstance(event, events.CommandReply):
            try:
                stream = self.stream_by_command.pop(event.command)
            except KeyError:
                raise
            if isinstance(event, events.OpenConnectionReply):
                self.connections[event.command.connection] = stream
            self.event_to_child(stream, event)
        elif isinstance(event, events.ConnectionEvent):
            handler = self.connections[event.connection]
            self.event_to_child(handler, event)
        else:
            raise ValueError(f"Unexpected event: {event}")

        while self.event_queue:
            event = self.event_queue.popleft()
            if isinstance(event, RequestHeaders):
                self.streams[event.stream_id] = self.make_stream()
            if isinstance(event, HttpEvent):
                stream = self.streams[event.stream_id]
                self.event_to_child(stream, event)
            elif isinstance(event, SendHttp):
                conn = self.connections[event.connection]
                evts = conn.send(event.event)
                self.event_queue.extend(evts)
            elif isinstance(event, GetHttpConnection):
                yield from self.get_connection(event)
            elif isinstance(event, commands.Command):
                yield event
            else:
                raise ValueError(f"Unexpected event: {event}")

    def get_connection(self, event: GetHttpConnection):
        # Do we already have a connection we can re-use?
        for connection, handler in self.connections.items():
            connection_suitable = (
                    event.connection_spec_matches(connection) and
                    (
                            isinstance(handler, Http2Client) or
                            # see "tricky multiplexing edge case" in make_http_connection for an explanation
                            isinstance(handler, Http1Client) and self.context.client.alpn != b"h2"
                    )
            )
            if connection_suitable:
                stream = self.stream_by_command.pop(event)
                self.event_to_child(stream, GetHttpConnectionReply(event, (connection, None)))
                return
        # Are we waiting for one?
        for connection in self.waiting_for_connection:
            if event.connection_spec_matches(connection):
                self.waiting_for_connection[connection].append(event)
                return
        # Can we reuse context.server?
        can_reuse_context_connection = (
                self.context.server.connected and
                self.context.server.tls == event.tls
        )
        if can_reuse_context_connection:
            self.waiting_for_connection[self.context.server].append(event)
            yield from self.make_http_connection(self.context.server)
        # We need a new one.
        else:
            connection = Server(event.address)
            connection.tls = event.tls
            self.waiting_for_connection[connection].append(event)
            open_command = commands.OpenConnection(connection)
            open_command.blocking = object()
            yield open_command

    def make_stream(self) -> HttpStream:
        ctx = self.context.fork()

        stream = HttpStream(ctx)
        if self.debug:
            stream.debug = self.debug + "  "
        self.event_to_child(stream, events.Start())
        return stream

    def make_http_connection(self, connection: Server) -> None:
        if connection.tls and not connection.tls_established:
            new_command = EstablishServerTLS(connection)
            new_command.blocking = object()
            yield new_command
            return

        if connection.alpn == b"h2":
            raise NotImplementedError
        else:
            self.connections[connection] = Http1Client(connection)

        waiting = self.waiting_for_connection.pop(connection)
        for cmd in waiting:
            stream = self.stream_by_command.pop(cmd)
            self.event_to_child(stream, GetHttpConnectionReply(cmd, (connection, None)))

            # Tricky multiplexing edge case: Assume a h2 client that sends two requests (or receives two responses)
            # that neither have a content-length specified nor a chunked transfer encoding.
            # We can't process these two flows to the same h1 connection as they would both have
            # "read until eof" semantics. We could force chunked transfer encoding for requests, but can't enforce that
            # for responses. The only workaround left is to open a separate connection for each flow.
            if self.context.client.alpn == b"h2" and connection.alpn != b"h2":
                for cmd in waiting[1:]:
                    new_connection = Server(connection.address)
                    new_connection.tls = connection.tls
                    self.waiting_for_connection[new_connection].append(cmd)
                    open_command = commands.OpenConnection(new_connection)
                    open_command.blocking = object()
                    yield open_command
                break

    def event_to_child(
            self,
            stream: typing.Union[Http1Connection, HttpStream],
            event: events.Event,
    ) -> None:
        stream_events = list(stream.handle_event(event))
        for se in stream_events:
            # Streams may yield blocking commands, which ultimately generate CommandReply events.
            # Those need to be routed back to the correct stream, so we need to keep track of that.
            if isinstance(se, commands.Command) and se.blocking:
                self.stream_by_command[se] = stream

        self.event_queue.extend(stream_events)
