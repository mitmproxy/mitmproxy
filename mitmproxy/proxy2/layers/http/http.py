import collections
import typing

from mitmproxy import flow, http
from mitmproxy.proxy.protocol.http import HTTPMode
from mitmproxy.proxy2 import commands, events
from mitmproxy.proxy2.context import Connection, Context, Server
from mitmproxy.proxy2.layer import Layer, NextLayer
from mitmproxy.proxy2.layers.tls import EstablishServerTLS, EstablishServerTLSReply, HTTP_ALPNS
from mitmproxy.proxy2.utils import expect
from mitmproxy.utils import human
from .base import HttpConnection, StreamId
from .events import HttpEvent, RequestData, RequestEndOfMessage, RequestHeaders, ResponseData, ResponseEndOfMessage, \
    ResponseHeaders
from .http1 import Http1Client, Http1Server
from .http2 import Http2Client


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
            else:
                self.flow.server_conn = connection

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
    connections: typing.Dict[Connection, typing.Union[HttpConnection, HttpStream]]
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
            if event.connection == self.context.server and self.context.server not in self.connections:
                pass
            else:
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

    def make_stream(self) -> HttpStream:
        ctx = self.context.fork()

        stream = HttpStream(ctx)
        if self.debug:
            stream.debug = self.debug + "  "
        self.event_to_child(stream, events.Start())
        return stream

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
                self.context.server not in self.connections and
                self.context.server.connected and
                self.context.server.address == event.address and
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

    def make_http_connection(self, connection: Server) -> None:
        if connection.tls and not connection.tls_established:
            connection.alpn_offers = list(HTTP_ALPNS)
            if not self.context.options.http2:
                connection.alpn_offers.remove(b"h2")
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
            stream: typing.Union[HttpConnection, HttpStream],
            event: events.Event,
    ) -> None:
        stream_events = list(stream.handle_event(event))
        for se in stream_events:
            # Streams may yield blocking commands, which ultimately generate CommandReply events.
            # Those need to be routed back to the correct stream, so we need to keep track of that.
            if isinstance(se, commands.Command) and se.blocking:
                self.stream_by_command[se] = stream

        self.event_queue.extend(stream_events)
