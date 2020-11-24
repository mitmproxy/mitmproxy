import collections
import time
import typing
from dataclasses import dataclass

from mitmproxy import flow, http
from mitmproxy.net import server_spec
from mitmproxy.net.http import url
from mitmproxy.proxy.protocol.http import HTTPMode
from mitmproxy.proxy2 import commands, events, layer, tunnel
from mitmproxy.proxy2.context import Connection, ConnectionState, Context, Server
from mitmproxy.proxy2.layers import tls
from mitmproxy.proxy2.layers.http import _upstream_proxy
from mitmproxy.proxy2.utils import expect
from mitmproxy.utils import human
from ._base import HttpCommand, HttpConnection, ReceiveHttp, StreamId
from ._events import HttpEvent, RequestData, RequestEndOfMessage, RequestHeaders, RequestProtocolError, ResponseData, \
    ResponseEndOfMessage, ResponseHeaders, ResponseProtocolError
from ._hooks import HttpConnectHook, HttpErrorHook, HttpRequestHeadersHook, HttpRequestHook, HttpResponseHeadersHook, \
    HttpResponseHook
from ._http1 import Http1Client, Http1Server
from ._http2 import Http2Client, Http2Server


def validate_request(mode, request) -> typing.Optional[str]:
    if request.scheme not in ("http", "https", ""):
        return f"Invalid request scheme: {request.scheme}"
    if mode is HTTPMode.transparent and request.method == "CONNECT":
        return (
            f"mitmproxy received an HTTP CONNECT request even though it is not running in regular/upstream mode. "
            f"This usually indicates a misconfiguration, please see the mitmproxy mode documentation for details."
        )
    return None


@dataclass
class GetHttpConnection(HttpCommand):
    """
    Open an HTTP Connection. This may not actually open a connection, but return an existing HTTP connection instead.
    """
    blocking = True
    address: typing.Tuple[str, int]
    tls: bool
    via: typing.Optional[server_spec.ServerSpec]

    def __hash__(self):
        return id(self)

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
        i = self.context.layers.index(self)
        parent: HttpLayer = self.context.layers[i - 1]
        return parent.mode

    def __init__(self, context: Context):
        super().__init__(context)
        self.request_body_buf = b""
        self.response_body_buf = b""
        self.client_state = self.state_uninitialized
        self.server_state = self.state_uninitialized

    def __repr__(self):
        return (
            f"HttpStream("
            f"id={self.stream_id}, "
            f"client_state={self.client_state.__name__}, "
            f"server_state={self.server_state.__name__}"
            f")"
        )

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
        # noinspection PyTypeChecker
        self.flow = http.HTTPFlow(
            self.context.client,
            self.context.server
        )
        self.flow.request = event.request

        if err := validate_request(self.mode, self.flow.request):
            self.flow.response = http.HTTPResponse.make(502, str(err))
            self.client_state = self.state_errored
            return (yield from self.send_response())

        if self.flow.request.method == "CONNECT":
            return (yield from self.handle_connect())

        if self.mode is HTTPMode.transparent:
            # Determine .scheme, .host and .port attributes for transparent requests
            self.flow.request.data.host = self.context.server.address[0]
            self.flow.request.data.port = self.context.server.address[1]
            self.flow.request.scheme = "https" if self.context.server.tls else "http"
        elif not self.flow.request.host:
            # We need to extract destination information from the host header.
            try:
                host, port = url.parse_authority(self.flow.request.host_header or "", check=True)
            except ValueError:
                self.flow.response = http.HTTPResponse.make(
                    400,
                    "HTTP request has no host header, destination unknown."
                )
                self.client_state = self.state_errored
                return (yield from self.send_response())
            else:
                if port is None:
                    port = 443 if self.context.client.tls else 80
                self.flow.request.data.host = host
                self.flow.request.data.port = port
                self.flow.request.scheme = "https" if self.context.client.tls else "http"

        if self.mode is HTTPMode.regular and not self.flow.request.is_http2:
            # Set the request target to origin-form for HTTP/1, some servers don't support absolute-form requests.
            # see https://github.com/mitmproxy/mitmproxy/issues/1759
            self.flow.request.authority = b""

        # update host header in reverse proxy mode
        if self.context.options.mode.startswith("reverse:") and not self.context.options.keep_host_header:
            self.flow.request.host_header = self.context.server.address[0]

        yield HttpRequestHeadersHook(self.flow)
        if (yield from self.check_killed()):
            return

        if self.flow.request.headers.get("expect", "").lower() == "100-continue":
            continue_response = http.HTTPResponse.make(100)
            continue_response.headers.clear()
            yield SendHttp(ResponseHeaders(self.stream_id, continue_response), self.context.client)
            self.flow.request.headers.pop("expect")

        if self.flow.request.stream:
            if self.flow.response:
                raise NotImplementedError("Can't set a response and enable streaming at the same time.")
            yield HttpRequestHook(self.flow)
            ok = yield from self.make_server_connection()
            if not ok:
                return
            yield SendHttp(event, self.context.server)
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
            self.flow.request.timestamp_end = time.time()
            yield SendHttp(RequestEndOfMessage(self.stream_id), self.context.server)
            self.client_state = self.state_done

    @expect(RequestData, RequestEndOfMessage)
    def state_consume_request_body(self, event: events.Event) -> layer.CommandGenerator[None]:
        if isinstance(event, RequestData):
            self.request_body_buf += event.data
        elif isinstance(event, RequestEndOfMessage):
            self.flow.request.timestamp_end = time.time()
            self.flow.request.data.content = self.request_body_buf
            self.request_body_buf = b""
            yield HttpRequestHook(self.flow)
            if (yield from self.check_killed()):
                return
            elif self.flow.response:
                # response was set by an inline script.
                # we now need to emulate the responseheaders hook.
                yield HttpResponseHeadersHook(self.flow)
                if (yield from self.check_killed()):
                    return
                yield from self.send_response()
            else:
                ok = yield from self.make_server_connection()
                if not ok:
                    return

                has_content = bool(self.flow.request.raw_content)
                yield SendHttp(RequestHeaders(self.stream_id, self.flow.request, not has_content), self.context.server)
                if has_content:
                    yield SendHttp(RequestData(self.stream_id, self.flow.request.raw_content), self.context.server)
                yield SendHttp(RequestEndOfMessage(self.stream_id), self.context.server)

            self.client_state = self.state_done

    @expect(ResponseHeaders)
    def state_wait_for_response_headers(self, event: ResponseHeaders) -> layer.CommandGenerator[None]:
        self.flow.response = event.response
        yield HttpResponseHeadersHook(self.flow)
        if (yield from self.check_killed()):
            return
        elif self.flow.response.stream:
            yield SendHttp(event, self.context.client)
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
            self.flow.response.timestamp_end = time.time()
            yield HttpResponseHook(self.flow)
            yield SendHttp(ResponseEndOfMessage(self.stream_id), self.context.client)
            self.server_state = self.state_done

    @expect(ResponseData, ResponseEndOfMessage)
    def state_consume_response_body(self, event: events.Event) -> layer.CommandGenerator[None]:
        if isinstance(event, ResponseData):
            self.response_body_buf += event.data
        elif isinstance(event, ResponseEndOfMessage):
            self.flow.response.timestamp_end = time.time()
            self.flow.response.data.content = self.response_body_buf
            self.response_body_buf = b""
            yield from self.send_response()
            self.server_state = self.state_done

    def check_killed(self) -> layer.CommandGenerator[bool]:
        killed_by_us = (
                self.flow.error and self.flow.error.msg == flow.Error.KILLED_MESSAGE
        )
        killed_by_remote = (
            self.context.client.state is not ConnectionState.OPEN
        )
        if killed_by_us or killed_by_remote:
            if self.context.client.state & ConnectionState.CAN_WRITE:
                yield commands.CloseConnection(self.context.client)
            self._handle_event = self.state_errored
            return True
        return False

    def send_response(self):
        yield HttpResponseHook(self.flow)
        if (yield from self.check_killed()):
            return
        has_content = bool(self.flow.response.raw_content)
        yield SendHttp(ResponseHeaders(self.stream_id, self.flow.response, not has_content), self.context.client)
        if has_content:
            yield SendHttp(ResponseData(self.stream_id, self.flow.response.raw_content), self.context.client)
        yield SendHttp(ResponseEndOfMessage(self.stream_id), self.context.client)

    def handle_protocol_error(
            self,
            event: typing.Union[RequestProtocolError, ResponseProtocolError]
    ) -> layer.CommandGenerator[None]:
        is_client_error_but_we_already_talk_upstream = (
            isinstance(event, RequestProtocolError) and
            self.client_state in (self.state_stream_request_body, self.state_done)
        )
        if is_client_error_but_we_already_talk_upstream:
            yield SendHttp(event, self.context.server)
            self.client_state = self.state_errored

        response_hook_already_triggered = (
            self.server_state in (self.state_done, self.state_errored)
        )
        if not response_hook_already_triggered:
            # We don't want to trigger both a response hook and an error hook,
            # so we need to check if the response is done yet or not.
            self.flow.error = flow.Error(event.message)
            yield HttpErrorHook(self.flow)

        if (yield from self.check_killed()):
            return

        if isinstance(event, ResponseProtocolError):
            yield SendHttp(event, self.context.client)
            self.server_state = self.state_errored

    def make_server_connection(self) -> layer.CommandGenerator[bool]:
        connection, err = yield GetHttpConnection(
            (self.flow.request.host, self.flow.request.port),
            self.flow.request.scheme == "https",
            self.context.server.via,
        )
        if err:
            yield from self.handle_protocol_error(ResponseProtocolError(self.stream_id, err))
            return False
        else:
            self.context.server = self.flow.server_conn = connection
            return True

    def handle_connect(self) -> layer.CommandGenerator[None]:
        yield HttpConnectHook(self.flow)
        if (yield from self.check_killed()):
            return

        self.context.server.address = (self.flow.request.host, self.flow.request.port)

        if self.mode == HTTPMode.regular:
            yield from self.handle_connect_regular()
        else:
            yield from self.handle_connect_upstream()

    def handle_connect_regular(self):
        if not self.flow.response and self.context.options.connection_strategy == "eager":
            err = yield commands.OpenConnection(self.context.server)
            if err:
                self.flow.response = http.HTTPResponse.make(
                    502, f"Cannot connect to {human.format_address(self.context.server.address)}: {err}"
                )
        self.child_layer = layer.NextLayer(self.context)
        yield from self.handle_connect_finish()

    def handle_connect_upstream(self):
        assert self.context.server.via.scheme in ("http", "https")

        http_proxy = Server(self.context.server.via.address)

        stack = tunnel.LayerStack()
        if self.context.server.via.scheme == "https":
            http_proxy.sni = self.context.server.via.address[0].encode()
            stack /= tls.ServerTLSLayer(self.context, http_proxy)
        stack /= _upstream_proxy.HttpUpstreamProxy(self.context, http_proxy, True)

        self.child_layer = stack[0]
        yield from self.handle_connect_finish()

    def handle_connect_finish(self):
        if not self.flow.response:
            self.flow.response = http.make_connect_response(self.flow.request.data.http_version)

        if 200 <= self.flow.response.status_code < 300:
            yield SendHttp(ResponseHeaders(self.stream_id, self.flow.response), self.context.client)
            self.child_layer = self.child_layer or layer.NextLayer(self.context)
            yield from self.child_layer.handle_event(events.Start())
            self._handle_event = self.passthrough
        else:
            yield from self.send_response()
            return (yield SendHttp(ResponseProtocolError(self.stream_id, "EOF"), self.context.client))

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
                yield SendHttp(ResponseProtocolError(self.stream_id, "EOF"), self.context.client)
            elif isinstance(command, commands.CloseConnection):
                # If we are running TCP over HTTP we want to be consistent with half-closes.
                # The easiest approach for this is to just always full close for now.
                # Alternatively, we could signal that we want a half close only through ResponseProtocolError,
                # but that is more complex to implement.
                command.half_close = False
                yield command
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
    command_sources: typing.Dict[commands.Command, layer.Layer]
    streams: typing.Dict[int, HttpStream]
    connections: typing.Dict[Connection, layer.Layer]
    waiting_for_establishment: typing.DefaultDict[Connection, typing.List[GetHttpConnection]]

    def __init__(self, context: Context, mode: HTTPMode):
        super().__init__(context)
        self.mode = mode

        self.waiting_for_establishment = collections.defaultdict(list)
        self.streams = {}
        self.command_sources = {}

        if self.context.client.alpn == b"h2":
            http_conn = Http2Server(context.fork())
        else:
            http_conn = Http1Server(context.fork())

        self.connections = {
            context.client: http_conn
        }

    def __repr__(self):
        return f"HttpLayer({self.mode.name}, conns: {len(self.connections)})"

    def _handle_event(self, event: events.Event):
        if isinstance(event, events.Start):
            yield from self.event_to_child(self.connections[self.context.client], event)
            if self.mode is HTTPMode.upstream:
                self.context.server.via = server_spec.parse_with_mode(self.context.options.mode)[1]
        elif isinstance(event, events.CommandReply):
            stream = self.command_sources.pop(event.command)
            yield from self.event_to_child(stream, event)
        elif isinstance(event, events.ConnectionEvent):
            if event.connection == self.context.server and self.context.server not in self.connections:
                # We didn't do anything with this connection yet, now the peer has closed it - let's close it too!
                yield commands.CloseConnection(event.connection)
            else:
                handler = self.connections[event.connection]
                yield from self.event_to_child(handler, event)
        else:
            raise AssertionError(f"Unexpected event: {event}")

    def event_to_child(
            self,
            child: typing.Union[layer.Layer, HttpStream],
            event: events.Event,
    ) -> layer.CommandGenerator[None]:
        for command in child.handle_event(event):
            assert isinstance(command, commands.Command)
            # Streams may yield blocking commands, which ultimately generate CommandReply events.
            # Those need to be routed back to the correct stream, so we need to keep track of that.

            if command.blocking:
                self.command_sources[command] = child

            if isinstance(command, ReceiveHttp):
                if isinstance(command.event, RequestHeaders):
                    self.streams[command.event.stream_id] = yield from self.make_stream()
                stream = self.streams[command.event.stream_id]
                yield from self.event_to_child(stream, command.event)
            elif isinstance(command, SendHttp):
                conn = self.connections[command.connection]
                yield from self.event_to_child(conn, command.event)
            elif isinstance(command, GetHttpConnection):
                yield from self.get_connection(command)
            elif isinstance(command, RegisterHttpConnection):
                yield from self.register_connection(command)
            elif isinstance(command, commands.OpenConnection):
                self.connections[command.connection] = child
                yield command
            elif isinstance(command, commands.Command):
                yield command
            else:
                raise AssertionError(f"Not a command: {event}")

    def make_stream(self) -> layer.CommandGenerator[HttpStream]:
        ctx = self.context.fork()
        stream = HttpStream(ctx)
        yield from self.event_to_child(stream, events.Start())
        return stream

    def get_connection(self, event: GetHttpConnection, *, reuse: bool = True) -> layer.CommandGenerator[None]:
        # Do we already have a connection we can re-use?
        if reuse:
            for connection in self.connections:
                # see "tricky multiplexing edge case" in make_http_connection for an explanation
                conn_is_pending_or_h2 = (
                    connection.alpn == b"h2"
                    or connection in self.waiting_for_establishment
                )
                h2_to_h1 = self.context.client.alpn == b"h2" and not conn_is_pending_or_h2
                connection_suitable = (
                        event.connection_spec_matches(connection)
                        and not h2_to_h1
                )
                if connection_suitable:
                    if connection in self.waiting_for_establishment:
                        self.waiting_for_establishment[connection].append(event)
                    else:
                        stream = self.command_sources.pop(event)
                        yield from self.event_to_child(stream, GetHttpConnectionReply(event, (connection, None)))
                    return

        can_use_context_connection = (
                self.context.server not in self.connections and
                self.context.server.connected and
                event.connection_spec_matches(self.context.server)
        )
        context = self.context.fork()

        stack = tunnel.LayerStack()

        if not can_use_context_connection:

            context.server = Server(event.address)

            if event.via:
                assert event.via.scheme in ("http", "https")
                http_proxy = Server(event.via.address)

                if event.via.scheme == "https":
                    http_proxy.sni = event.via.address[0].encode()
                    stack /= tls.ServerTLSLayer(context, http_proxy)

                send_connect = not (self.mode == HTTPMode.upstream and not event.tls)
                stack /= _upstream_proxy.HttpUpstreamProxy(context, http_proxy, send_connect)
            if event.tls:
                stack /= tls.ServerTLSLayer(context)

        stack /= HttpClient(context)

        self.connections[context.server] = stack[0]
        self.waiting_for_establishment[context.server].append(event)

        yield from self.event_to_child(stack[0], events.Start())

    def register_connection(self, command: RegisterHttpConnection) -> layer.CommandGenerator[None]:
        waiting = self.waiting_for_establishment.pop(command.connection)

        if command.err:
            reply = (None, command.err)
        else:
            reply = (command.connection, None)

        for cmd in waiting:
            stream = self.command_sources.pop(cmd)
            yield from self.event_to_child(stream, GetHttpConnectionReply(cmd, reply))

            # Somewhat ugly edge case: If we do HTTP/2 -> HTTP/1 proxying we don't want
            # to handle everything over a single connection.
            # Tricky multiplexing edge case: Assume we are doing HTTP/2 -> HTTP/1 proxying,
            #
            # that receives two responses
            # that neither have a content-length specified nor a chunked transfer encoding.
            # We can't process these two flows to the same h1 connection as they would both have
            # "read until eof" semantics. The only workaround left is to open a separate connection for each flow.
            if not command.err and self.context.client.alpn == b"h2" and command.connection.alpn != b"h2":
                for cmd in waiting[1:]:
                    yield from self.get_connection(cmd, reuse=False)
                break


class HttpClient(layer.Layer):
    @expect(events.Start)
    def _handle_event(self, event: events.Event) -> layer.CommandGenerator[None]:
        if self.context.server.connected:
            err = None
        else:
            err = yield commands.OpenConnection(self.context.server)
        if not err:
            if self.context.server.alpn == b"h2":
                child_layer = Http2Client(self.context)
            else:
                child_layer = Http1Client(self.context)
            self._handle_event = child_layer.handle_event
            yield from self._handle_event(event)
        yield RegisterHttpConnection(self.context.server, err)
