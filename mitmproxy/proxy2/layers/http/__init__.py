import collections
import typing
from dataclasses import dataclass

from mitmproxy import flow, http
from mitmproxy.net import server_spec
from mitmproxy.proxy.protocol.http import HTTPMode
from mitmproxy.proxy2 import commands, events, layer, tunnel
from mitmproxy.proxy2.context import Connection, Context, Server
from mitmproxy.proxy2.layers import tls
from mitmproxy.proxy2.layers.http import upstream_proxy
from mitmproxy.proxy2.utils import expect
from mitmproxy.utils import human
from ._base import HttpCommand, HttpConnection, ReceiveHttp, StreamId
from ._events import HttpEvent, RequestData, RequestEndOfMessage, RequestHeaders, RequestProtocolError, ResponseData, \
    ResponseEndOfMessage, ResponseHeaders, ResponseProtocolError
from ._hooks import HttpConnectHook, HttpErrorHook, HttpRequestHeadersHook, HttpRequestHook, HttpResponseHeadersHook, \
    HttpResponseHook
from ._http1 import Http1Client, Http1Server
from ._http2 import Http2Client


class GetHttpConnection(HttpCommand):
    """
    Open a HTTP Connection. This may not actually open a connection, but return an existing HTTP connection instead.
    """
    blocking = True
    address: typing.Tuple[str, int]
    tls: bool
    via: typing.Sequence[server_spec.ServerSpec]

    def __init__(self, address: typing.Tuple[str, int], tls: bool, via: typing.Sequence[str]):
        self.address = address
        self.tls = tls
        self.via = tuple(via)

    def connection_spec_matches(self, connection: Connection) -> bool:
        return (
                isinstance(connection, Server)
                and
                self.address == connection.address
                and
                self.tls == connection.tls
                and
                self.via == connection.via
        )


@dataclass
class GetHttpConnectionReply(events.CommandReply):
    command: GetHttpConnection
    reply: typing.Tuple[typing.Optional[Connection], typing.Optional[str]]
    """connection object, error message"""


class RegisterHttpConnection(HttpCommand):
    """
    Register that a HTTP connection has been successfully established.
    """
    connection: Connection
    err: str

    def __init__(self, connection: Connection, err: str):
        self.connection = connection
        self.err = err


class SendHttp(HttpCommand):
    connection: Connection
    event: HttpEvent

    def __init__(self, event: HttpEvent, connection: Connection):
        self.connection = connection
        self.event = event

    def __repr__(self) -> str:
        return f"Send({self.event})"


class HttpStream(layer.Layer):
    request_body_buf: bytes
    response_body_buf: bytes
    flow: http.HTTPFlow
    stream_id: StreamId
    child_layer: typing.Optional[layer.Layer] = None

    @property
    def mode(self):
        parent: HttpLayer = self.context.layers[-2]
        return parent.mode

    def __init__(self, context: Context):
        super().__init__(context)
        self.request_body_buf = b""
        self.response_body_buf = b""
        self.client_state = self.state_uninitialized
        self.server_state = self.state_uninitialized

    @expect(events.Start, HttpEvent)
    def _handle_event(self, event: events.Event) -> layer.CommandGenerator[None]:
        if isinstance(event, events.Start):
            self.client_state = self.state_wait_for_request_headers
        elif isinstance(event, (RequestProtocolError, ResponseProtocolError)):
            yield from self.handle_protocol_error(event)
        elif isinstance(event, (RequestHeaders, RequestData, RequestEndOfMessage)):
            yield from self.client_state(event)
        else:
            yield from self.server_state(event)

    @expect(RequestHeaders)
    def state_wait_for_request_headers(self, event: RequestHeaders) -> layer.CommandGenerator[None]:
        self.stream_id = event.stream_id
        self.flow = http.HTTPFlow(
            self.context.client,
            self.context.server
        )
        self.flow.request = event.request

        if self.flow.request.first_line_format == "authority":
            yield from self.handle_connect()
            return

        if self.flow.request.headers.get("expect", "").lower() == "100-continue":
            raise NotImplementedError("expect nothing")
            # self.send_response(http.expect_continue_response)
            # request.headers.pop("expect")

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

        self.flow.request.via = []  # FIXME: Make this an official attribute.
        if self.context.options.mode.startswith("upstream:"):
            self.flow.request.via.append(
                server_spec.parse_with_mode(self.context.options.mode)[1]
            )

        yield HttpRequestHeadersHook(self.flow)

        if self.flow.request.stream:
            if self.flow.response:
                raise NotImplementedError("Can't set a response and enable streaming at the same time.")
            ok = yield from self.make_server_connection()
            if not ok:
                return
            yield SendHttp(RequestHeaders(self.stream_id, self.flow.request), self.context.server)
            self.client_state = self.state_stream_request_body
        else:
            self.client_state = self.state_consume_request_body
        self.server_state = self.state_wait_for_response_headers

    @expect(RequestData, RequestEndOfMessage)
    def state_stream_request_body(self, event: events.Event) -> layer.CommandGenerator[None]:
        if isinstance(event, RequestData):
            if callable(self.flow.request.stream):
                data = self.flow.request.stream(event.data)
            else:
                data = event.data
            yield SendHttp(RequestData(self.stream_id, data), self.context.server)
        elif isinstance(event, RequestEndOfMessage):
            yield SendHttp(RequestEndOfMessage(self.stream_id), self.context.server)
            self.client_state = self.state_done

    @expect(RequestData, RequestEndOfMessage)
    def state_consume_request_body(self, event: events.Event) -> layer.CommandGenerator[None]:
        if isinstance(event, RequestData):
            self.request_body_buf += event.data
        elif isinstance(event, RequestEndOfMessage):
            self.flow.request.data.content = self.request_body_buf
            self.request_body_buf = b""
            yield HttpRequestHook(self.flow)
            if self.flow.response:
                # response was set by an inline script.
                # we now need to emulate the responseheaders hook.
                yield HttpResponseHeadersHook(self.flow)
                yield from self.send_response()
            else:
                ok = yield from self.make_server_connection()
                if not ok:
                    return

                yield SendHttp(RequestHeaders(self.stream_id, self.flow.request), self.context.server)
                yield SendHttp(RequestData(self.stream_id, self.flow.request.data.content), self.context.server)
                yield SendHttp(RequestEndOfMessage(self.stream_id), self.context.server)

            self.client_state = self.state_done

    @expect(ResponseHeaders)
    def state_wait_for_response_headers(self, event: ResponseHeaders) -> layer.CommandGenerator[None]:
        self.flow.response = event.response
        yield HttpResponseHeadersHook(self.flow)
        if self.flow.response.stream:
            yield SendHttp(ResponseHeaders(self.stream_id, self.flow.response), self.context.client)
            self.server_state = self.state_stream_response_body
        else:
            self.server_state = self.state_consume_response_body

    @expect(ResponseData, ResponseEndOfMessage)
    def state_stream_response_body(self, event: events.Event) -> layer.CommandGenerator[None]:
        if isinstance(event, ResponseData):
            if callable(self.flow.response.stream):
                data = self.flow.response.stream(event.data)
            else:
                data = event.data
            yield SendHttp(ResponseData(self.stream_id, data), self.context.client)
        elif isinstance(event, ResponseEndOfMessage):
            yield SendHttp(ResponseEndOfMessage(self.stream_id), self.context.client)
            self.server_state = self.state_done

    @expect(ResponseData, ResponseEndOfMessage)
    def state_consume_response_body(self, event: events.Event) -> layer.CommandGenerator[None]:
        if isinstance(event, ResponseData):
            self.response_body_buf += event.data
        elif isinstance(event, ResponseEndOfMessage):
            self.flow.response.data.content = self.response_body_buf
            self.response_body_buf = b""
            yield from self.send_response()

    def send_response(self):
        yield HttpResponseHook(self.flow)
        yield SendHttp(ResponseHeaders(self.stream_id, self.flow.response), self.context.client)
        yield SendHttp(ResponseData(self.stream_id, self.flow.response.data.content), self.context.client)
        yield SendHttp(ResponseEndOfMessage(self.stream_id), self.context.client)
        self.server_state = self.state_done

    def handle_protocol_error(
            self,
            event: typing.Union[RequestProtocolError, ResponseProtocolError]
    ) -> layer.CommandGenerator[None]:
        self.flow.error = flow.Error(event.message)
        yield HttpErrorHook(self.flow)

        if isinstance(event, RequestProtocolError):
            yield SendHttp(event, self.context.server)
        else:
            yield SendHttp(event, self.context.client)
        return

    def make_server_connection(self) -> layer.CommandGenerator[bool]:
        connection, err = yield GetHttpConnection(
            (self.flow.request.host, self.flow.request.port),
            self.flow.request.scheme == "https",
            self.flow.request.via,
        )
        if err:
            yield from self.handle_protocol_error(ResponseProtocolError(self.stream_id, err))
            return False
        else:
            self.context.server = self.flow.server_conn = connection
            return True

    def handle_connect(self) -> layer.CommandGenerator[None]:
        yield HttpConnectHook(self.flow)

        self.context.server = Server((self.flow.request.host, self.flow.request.port))
        if self.context.options.connection_strategy == "eager":
            err = yield commands.OpenConnection(self.context.server)
            if err:
                self.flow.response = http.HTTPResponse.make(
                    502, f"Cannot connect to {human.format_address(self.context.server.address)}: {err}"
                )

        if not self.flow.response:
            self.flow.response = http.make_connect_response(self.flow.request.data.http_version)

        yield SendHttp(ResponseHeaders(self.stream_id, self.flow.response), self.context.client)

        if 200 <= self.flow.response.status_code < 300:
            self.child_layer = layer.NextLayer(self.context)
            yield from self.child_layer.handle_event(events.Start())
            self._handle_event = self.passthrough
        else:
            yield SendHttp(ResponseData(self.stream_id, self.flow.response.data.content), self.context.client)
            yield SendHttp(ResponseEndOfMessage(self.stream_id), self.context.client)

    @expect(RequestData, RequestEndOfMessage, events.Event)
    def passthrough(self, event: events.Event) -> layer.CommandGenerator[None]:
        # HTTP events -> normal connection events
        if isinstance(event, RequestData):
            event = events.DataReceived(self.context.client, event.data)
        elif isinstance(event, RequestEndOfMessage):
            event = events.ConnectionClosed(self.context.client)

        for command in self.child_layer.handle_event(event):
            # normal connection events -> HTTP events
            if isinstance(command, commands.SendData) and command.connection == self.context.client:
                yield SendHttp(ResponseData(self.stream_id, command.data), self.context.client)
            elif isinstance(command, commands.CloseConnection) and command.connection == self.context.client:
                yield SendHttp(ResponseEndOfMessage(self.stream_id), self.context.client)
            else:
                yield command

    @expect()
    def state_uninitialized(self, _) -> layer.CommandGenerator[None]:
        yield from ()

    @expect()
    def state_done(self, _) -> layer.CommandGenerator[None]:
        yield from ()

    def state_errored(self, _) -> layer.CommandGenerator[None]:
        # silently consume every event.
        yield from ()


class HttpLayer(layer.Layer):
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
    connections: typing.Dict[Connection, typing.Union[layer.Layer, HttpStream]]
    waiting_for_establishment: typing.DefaultDict[Connection, typing.List[GetHttpConnection]]
    command_queue: typing.Deque[commands.Command]

    def __init__(self, context: Context, mode: HTTPMode):
        super().__init__(context)
        self.mode = mode

        self.waiting_for_establishment = collections.defaultdict(list)
        self.streams = {}
        self.stream_by_command = {}
        self.command_queue = collections.deque()

        self.connections = {
            context.client: Http1Server(context.fork())
        }

    def __repr__(self):
        return f"HttpLayer(conns: {len(self.connections)}, queue: {[type(e).__name__ for e in self.command_queue]})"

    def _handle_event(self, event: events.Event):
        if isinstance(event, events.Start):
            return
        elif isinstance(event, events.CommandReply):
            stream = self.stream_by_command.pop(event.command)
            self.event_to_child(stream, event)
        elif isinstance(event, events.ConnectionEvent):
            if event.connection == self.context.server and self.context.server not in self.connections:
                pass
            else:
                try:
                    handler = self.connections[event.connection]
                except KeyError:
                    raise
                self.event_to_child(handler, event)
        else:
            raise ValueError(f"Unexpected event: {event}")

        while self.command_queue:
            command = self.command_queue.popleft()
            if isinstance(command, ReceiveHttp):
                if isinstance(command.event, RequestHeaders):
                    self.streams[command.event.stream_id] = self.make_stream()
                stream = self.streams[command.event.stream_id]
                self.event_to_child(stream, command.event)
            elif isinstance(command, SendHttp):
                conn = self.connections[command.connection]
                self.event_to_child(conn, command.event)
            elif isinstance(command, GetHttpConnection):
                self.get_connection(command)
            elif isinstance(command, RegisterHttpConnection):
                yield from self.register_connection(command)
            elif isinstance(command, commands.Command):
                yield command
            else:  # pragma: no cover
                raise ValueError(f"Not a command command: {command}")

    def make_stream(self) -> HttpStream:
        ctx = self.context.fork()
        stream = HttpStream(ctx)
        self.event_to_child(stream, events.Start())
        return stream

    def get_connection(self, event: GetHttpConnection, *, reuse: bool = True):
        # Do we already have a connection we can re-use?
        for connection in self.connections:
            # see "tricky multiplexing edge case" in make_http_connection for an explanation
            not_h2_to_h1 = connection.alpn == b"h2" or self.context.client.alpn != b"h2"
            connection_suitable = (
                    reuse and
                    event.connection_spec_matches(connection) and
                    not_h2_to_h1
            )
            if connection_suitable:
                if connection in self.waiting_for_establishment:
                    self.waiting_for_establishment[connection].append(event)
                else:
                    stream = self.stream_by_command.pop(event)
                    self.event_to_child(stream, GetHttpConnectionReply(event, (connection, None)))
                return

        can_reuse_context_connection = (
                self.context.server not in self.connections and
                self.context.server.connected and
                event.connection_spec_matches(self.context.server)
        )
        context = self.context.fork()

        stack = tunnel.LayerStack()

        if not can_reuse_context_connection:
            context.server = Server(event.address)
            if context.options.http2:
                context.server.alpn_offers = tls.HTTP_ALPNS
            else:
                context.server.alpn_offers = tls.HTTP1_ALPNS

            for via in reversed(event.via):
                stack /= upstream_proxy.HttpUpstreamProxy(context, via.address)
            if event.tls:
                stack /= tls.ServerTLSLayer(context)

        stack /= HttpClient(context)

        self.connections[context.server] = stack[0]
        self.waiting_for_establishment[context.server].append(event)

        self.event_to_child(stack[0], events.Start())

    def register_connection(self, command: RegisterHttpConnection):
        waiting = self.waiting_for_establishment.pop(command.connection)

        if command.err:
            reply = (None, command.err)
        else:
            reply = (command.connection, None)

        for cmd in waiting:
            stream = self.stream_by_command.pop(cmd)
            self.event_to_child(stream, GetHttpConnectionReply(cmd, reply))

            # Tricky multiplexing edge case: Assume a h2 client that sends two requests (or receives two responses)
            # that neither have a content-length specified nor a chunked transfer encoding.
            # We can't process these two flows to the same h1 connection as they would both have
            # "read until eof" semantics. We could force chunked transfer encoding for requests, but can't enforce that
            # for responses. The only workaround left is to open a separate connection for each flow.
            if not command.err and self.context.client.alpn == b"h2" and command.connection.alpn != b"h2":
                for cmd in waiting[1:]:
                    yield from self.get_connection(cmd, reuse=False)
                break

    def event_to_child(
            self,
            child: typing.Union[layer.Layer, HttpStream],
            event: events.Event,
    ) -> None:
        child_commands = list(child.handle_event(event))
        for cmd in child_commands:
            assert isinstance(cmd, commands.Command)
            # Streams may yield blocking commands, which ultimately generate CommandReply events.
            # Those need to be routed back to the correct stream, so we need to keep track of that.
            if isinstance(cmd, commands.OpenConnection):
                self.connections[cmd.connection] = child

            if cmd.blocking:
                self.stream_by_command[cmd] = child

        self.command_queue.extend(child_commands)


class HttpClient(layer.Layer):
    @expect(events.Start)
    def _handle_event(self, event: events.Event) -> layer.CommandGenerator[None]:
        if self.context.server.connected:
            err = None
        else:
            err = yield commands.OpenConnection(self.context.server)
        yield RegisterHttpConnection(self.context.server, err)
        if err:
            return

        if self.context.server.alpn == b"h2":
            raise NotImplementedError
        else:
            child_layer = Http1Client(self.context)
            self._handle_event = child_layer.handle_event
        yield from self._handle_event(event)