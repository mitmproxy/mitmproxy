import collections
import enum
import time
from dataclasses import dataclass
from typing import DefaultDict, Dict, List, Optional, Tuple, Union

import wsproto.handshake
from mitmproxy import flow, http
from mitmproxy.connection import Connection, Server
from mitmproxy.net import server_spec
from mitmproxy.net.http import status_codes, url
from mitmproxy.net.http.http1 import expected_http_body_size
from mitmproxy.proxy import commands, events, layer, tunnel
from mitmproxy.proxy.layers import tcp, tls, websocket
from mitmproxy.proxy.layers.http import _upstream_proxy
from mitmproxy.proxy.utils import expect
from mitmproxy.utils import human
from mitmproxy.websocket import WebSocketData
from ._base import HttpCommand, HttpConnection, ReceiveHttp, StreamId
from ._events import HttpEvent, RequestData, RequestEndOfMessage, RequestHeaders, RequestProtocolError, RequestTrailers, \
    ResponseData, ResponseEndOfMessage, ResponseHeaders, ResponseProtocolError, ResponseTrailers
from ._hooks import HttpConnectHook, HttpErrorHook, HttpRequestHeadersHook, HttpRequestHook, HttpResponseHeadersHook, \
    HttpResponseHook, HttpConnectUpstreamHook  # noqa
from ._http1 import Http1Client, Http1Connection, Http1Server
from ._http2 import Http2Client, Http2Server
from ...context import Context


class HTTPMode(enum.Enum):
    regular = 1
    transparent = 2
    upstream = 3


def validate_request(mode, request) -> Optional[str]:
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
    address: Tuple[str, int]
    tls: bool
    via: Optional[server_spec.ServerSpec]

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
class GetHttpConnectionCompleted(events.CommandCompleted):
    command: GetHttpConnection
    reply: Union[Tuple[None, str], Tuple[Connection, None]]
    """connection object, error message"""


@dataclass
class RegisterHttpConnection(HttpCommand):
    """
    Register that a HTTP connection attempt has been completed.
    """
    connection: Connection
    err: Optional[str]


@dataclass
class SendHttp(HttpCommand):
    event: HttpEvent
    connection: Connection

    def __repr__(self) -> str:
        return f"Send({self.event})"


class HttpStream(layer.Layer):
    request_body_buf: bytes
    response_body_buf: bytes
    flow: http.HTTPFlow
    stream_id: StreamId
    child_layer: Optional[layer.Layer] = None

    @property
    def mode(self):
        i = self.context.layers.index(self)
        parent: HttpLayer = self.context.layers[i - 1]
        return parent.mode

    def __init__(self, context: Context, stream_id: int):
        super().__init__(context)
        self.request_body_buf = b""
        self.response_body_buf = b""
        self.client_state = self.state_uninitialized
        self.server_state = self.state_uninitialized
        self.stream_id = stream_id

    def __repr__(self):
        if self._handle_event == self.passthrough:
            return f"HttpStream(id={self.stream_id}, passthrough)"
        else:
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
        elif isinstance(event, (RequestHeaders, RequestData, RequestTrailers, RequestEndOfMessage)):
            yield from self.client_state(event)
        else:
            yield from self.server_state(event)

    @expect(RequestHeaders)
    def state_wait_for_request_headers(self, event: RequestHeaders) -> layer.CommandGenerator[None]:
        if not event.replay_flow:
            self.flow = http.HTTPFlow(
                self.context.client,
                self.context.server
            )

        else:
            self.flow = event.replay_flow
        self.flow.request = event.request

        if err := validate_request(self.mode, self.flow.request):
            self.flow.response = http.Response.make(502, str(err))
            self.client_state = self.state_errored
            return (yield from self.send_response())

        if self.flow.request.method == "CONNECT":
            return (yield from self.handle_connect())

        if self.mode is HTTPMode.transparent:
            # Determine .scheme, .host and .port attributes for transparent requests
            assert self.context.server.address
            self.flow.request.data.host = self.context.server.address[0]
            self.flow.request.data.port = self.context.server.address[1]
            self.flow.request.scheme = "https" if self.context.server.tls else "http"
        elif not self.flow.request.host:
            # We need to extract destination information from the host header.
            try:
                host, port = url.parse_authority(self.flow.request.host_header or "", check=True)
            except ValueError:
                yield SendHttp(
                    ResponseProtocolError(self.stream_id, "HTTP request has no host header, destination unknown.", 400),
                    self.context.client
                )
                self.client_state = self.state_errored
                return
            else:
                if port is None:
                    port = 443 if self.context.client.tls else 80
                self.flow.request.data.host = host
                self.flow.request.data.port = port
                self.flow.request.scheme = "https" if self.context.client.tls else "http"

        if self.mode is HTTPMode.regular and not self.flow.request.is_http2:
            # Set the request target to origin-form for HTTP/1, some servers don't support absolute-form requests.
            # see https://github.com/mitmproxy/mitmproxy/issues/1759
            self.flow.request.authority = ""

        # update host header in reverse proxy mode
        if self.context.options.mode.startswith("reverse:") and not self.context.options.keep_host_header:
            assert self.context.server.address
            self.flow.request.host_header = url.hostport(
                "https" if self.context.server.tls else "http",
                self.context.server.address[0],
                self.context.server.address[1],
            )

        if not event.end_stream and (yield from self.check_body_size(True)):
            return

        yield HttpRequestHeadersHook(self.flow)
        if (yield from self.check_killed(True)):
            return

        if self.flow.request.headers.get("expect", "").lower() == "100-continue":
            continue_response = http.Response.make(100)
            continue_response.headers.clear()
            yield SendHttp(ResponseHeaders(self.stream_id, continue_response), self.context.client)
            self.flow.request.headers.pop("expect")

        if self.flow.request.stream:
            yield from self.start_request_stream()
        else:
            self.client_state = self.state_consume_request_body
        self.server_state = self.state_wait_for_response_headers

    def start_request_stream(self) -> layer.CommandGenerator[None]:
        if self.flow.response:
            raise NotImplementedError("Can't set a response and enable streaming at the same time.")
        ok = yield from self.make_server_connection()
        if not ok:
            return
        yield SendHttp(
            RequestHeaders(self.stream_id, self.flow.request, end_stream=False),
            self.context.server
        )
        yield commands.Log(f"Streaming request to {self.flow.request.host}.")
        self.client_state = self.state_stream_request_body

    @expect(RequestData, RequestTrailers, RequestEndOfMessage)
    def state_stream_request_body(self, event: Union[RequestData, RequestEndOfMessage]) -> layer.CommandGenerator[None]:
        if isinstance(event, RequestData):
            if callable(self.flow.request.stream):
                chunks = self.flow.request.stream(event.data)
                if isinstance(chunks, bytes):
                    chunks = [chunks]
            else:
                chunks = [event.data]
            for chunk in chunks:
                yield SendHttp(RequestData(self.stream_id, chunk), self.context.server)
        elif isinstance(event, RequestTrailers):
            # we don't do anything further here, we wait for RequestEndOfMessage first to trigger the request hook.
            self.flow.request.trailers = event.trailers
        elif isinstance(event, RequestEndOfMessage):
            if callable(self.flow.request.stream):
                chunks = self.flow.request.stream(b"")
                if isinstance(chunks, bytes):
                    chunks = [chunks]
                for chunk in chunks:
                    yield SendHttp(RequestData(self.stream_id, chunk), self.context.server)

            self.flow.request.timestamp_end = time.time()
            yield HttpRequestHook(self.flow)
            self.client_state = self.state_done

            if self.flow.request.trailers:
                # we've delayed sending trailers until after `request` has been triggered.
                yield SendHttp(RequestTrailers(self.stream_id, self.flow.request.trailers), self.context.server)
            yield SendHttp(event, self.context.server)

    @expect(RequestData, RequestTrailers, RequestEndOfMessage)
    def state_consume_request_body(self, event: events.Event) -> layer.CommandGenerator[None]:
        if isinstance(event, RequestData):
            self.request_body_buf += event.data
            yield from self.check_body_size(True)
        elif isinstance(event, RequestTrailers):
            assert self.flow.request
            self.flow.request.trailers = event.trailers
        elif isinstance(event, RequestEndOfMessage):
            self.flow.request.timestamp_end = time.time()
            self.flow.request.data.content = self.request_body_buf
            self.request_body_buf = b""
            self.client_state = self.state_done
            yield HttpRequestHook(self.flow)
            if (yield from self.check_killed(True)):
                return
            elif self.flow.response:
                # response was set by an inline script.
                # we now need to emulate the responseheaders hook.
                self.flow.response.timestamp_start = time.time()
                yield HttpResponseHeadersHook(self.flow)
                if (yield from self.check_killed(True)):
                    return
                yield from self.send_response()
            else:
                ok = yield from self.make_server_connection()
                if not ok:
                    return

                content = self.flow.request.raw_content
                done_after_headers = not (content or self.flow.request.trailers)
                yield SendHttp(RequestHeaders(self.stream_id, self.flow.request, done_after_headers), self.context.server)
                if content:
                    yield SendHttp(RequestData(self.stream_id, content), self.context.server)
                if self.flow.request.trailers:
                    yield SendHttp(RequestTrailers(self.stream_id, self.flow.request.trailers), self.context.server)
                yield SendHttp(RequestEndOfMessage(self.stream_id), self.context.server)

    @expect(ResponseHeaders)
    def state_wait_for_response_headers(self, event: ResponseHeaders) -> layer.CommandGenerator[None]:
        self.flow.response = event.response

        if not event.end_stream and (yield from self.check_body_size(False)):
            return

        yield HttpResponseHeadersHook(self.flow)
        if (yield from self.check_killed(True)):
            return

        elif self.flow.response.stream:
            yield from self.start_response_stream()
        else:
            self.server_state = self.state_consume_response_body

    def start_response_stream(self) -> layer.CommandGenerator[None]:
        assert self.flow.response
        yield SendHttp(ResponseHeaders(self.stream_id, self.flow.response, end_stream=False), self.context.client)
        yield commands.Log(f"Streaming response from {self.flow.request.host}.")
        self.server_state = self.state_stream_response_body

    @expect(ResponseData, ResponseTrailers, ResponseEndOfMessage)
    def state_stream_response_body(self, event: events.Event) -> layer.CommandGenerator[None]:
        assert self.flow.response
        if isinstance(event, ResponseData):
            if callable(self.flow.response.stream):
                chunks = self.flow.response.stream(event.data)
                if isinstance(chunks, bytes):
                    chunks = [chunks]
            else:
                chunks = [event.data]
            for chunk in chunks:
                yield SendHttp(ResponseData(self.stream_id, chunk), self.context.client)
        elif isinstance(event, ResponseTrailers):
            self.flow.response.trailers = event.trailers
            # will be sent in send_response() after the response hook.
        elif isinstance(event, ResponseEndOfMessage):
            if callable(self.flow.response.stream):
                chunks = self.flow.response.stream(b"")
                if isinstance(chunks, bytes):
                    chunks = [chunks]
                for chunk in chunks:
                    yield SendHttp(ResponseData(self.stream_id, chunk), self.context.client)
            yield from self.send_response(already_streamed=True)

    @expect(ResponseData, ResponseTrailers, ResponseEndOfMessage)
    def state_consume_response_body(self, event: events.Event) -> layer.CommandGenerator[None]:
        if isinstance(event, ResponseData):
            self.response_body_buf += event.data
            yield from self.check_body_size(False)
        elif isinstance(event, ResponseTrailers):
            assert self.flow.response
            self.flow.response.trailers = event.trailers
        elif isinstance(event, ResponseEndOfMessage):
            assert self.flow.response
            self.flow.response.data.content = self.response_body_buf
            self.response_body_buf = b""
            yield from self.send_response()

    def send_response(self, already_streamed: bool = False):
        """We have either consumed the entire response from the server or the response was set by an addon."""
        assert self.flow.response
        self.flow.response.timestamp_end = time.time()

        is_websocket = (
            self.flow.response.status_code == 101
            and
            self.flow.response.headers.get("upgrade", "").lower() == "websocket"
            and
            self.flow.request.headers.get("Sec-WebSocket-Version", "").encode() == wsproto.handshake.WEBSOCKET_VERSION
            and
            self.context.options.websocket
        )
        if is_websocket:
            # We need to set this before calling the response hook
            # so that addons can determine if a WebSocket connection is following up.
            self.flow.websocket = WebSocketData()

        yield HttpResponseHook(self.flow)
        self.server_state = self.state_done
        if (yield from self.check_killed(False)):
            return

        if not already_streamed:
            content = self.flow.response.raw_content
            done_after_headers = not (content or self.flow.response.trailers)
            yield SendHttp(ResponseHeaders(self.stream_id, self.flow.response, done_after_headers), self.context.client)
            if content:
                yield SendHttp(ResponseData(self.stream_id, content), self.context.client)

        if self.flow.response.trailers:
            yield SendHttp(ResponseTrailers(self.stream_id, self.flow.response.trailers), self.context.client)
        yield SendHttp(ResponseEndOfMessage(self.stream_id), self.context.client)

        if self.flow.response.status_code == 101:
            if is_websocket:
                self.child_layer = websocket.WebsocketLayer(self.context, self.flow)
            elif self.context.options.rawtcp:
                self.child_layer = tcp.TCPLayer(self.context)
            else:
                yield commands.Log(f"Sent HTTP 101 response, but no protocol is enabled to upgrade to.", "warn")
                yield commands.CloseConnection(self.context.client)
                self.client_state = self.server_state = self.state_errored
                return
            if self.debug:
                yield commands.Log(f"{self.debug}[http] upgrading to {self.child_layer}", "debug")
            yield from self.child_layer.handle_event(events.Start())
            self._handle_event = self.passthrough
            return

    def check_body_size(self, request: bool) -> layer.CommandGenerator[bool]:
        """
        Check if the body size exceeds limits imposed by stream_large_bodies or body_size_limit.

        Returns `True` if the body size exceeds body_size_limit and further processing should be stopped.
        """
        if not (self.context.options.stream_large_bodies or self.context.options.body_size_limit):
            return False

        # Step 1: Determine the expected body size. This can either come from a known content-length header,
        # or from the amount of currently buffered bytes (e.g. for chunked encoding).
        response = not request
        expected_size: Optional[int]
        # the 'late' case: we already started consuming the body
        if request and self.request_body_buf:
            expected_size = len(self.request_body_buf)
        elif response and self.response_body_buf:
            expected_size = len(self.response_body_buf)
        else:
            # the 'early' case: we have not started consuming the body
            try:
                expected_size = expected_http_body_size(self.flow.request, self.flow.response if response else None)
            except ValueError:  # pragma: no cover
                # we just don't stream/kill malformed content-length headers.
                expected_size = None

        if expected_size is None or expected_size <= 0:
            return False

        # Step 2: Do we need to abort this?
        max_total_size = human.parse_size(self.context.options.body_size_limit)
        if max_total_size is not None and expected_size > max_total_size:
            if request and not self.request_body_buf:
                yield HttpRequestHeadersHook(self.flow)
            if response and not self.response_body_buf:
                yield HttpResponseHeadersHook(self.flow)

            err_msg = f"{'Request' if request else 'Response'} body exceeds mitmproxy's body_size_limit."
            err_code = 413 if request else 502

            self.flow.error = flow.Error(err_msg)
            yield HttpErrorHook(self.flow)
            yield SendHttp(ResponseProtocolError(self.stream_id, err_msg, err_code), self.context.client)
            self.client_state = self.state_errored
            if response:
                yield SendHttp(RequestProtocolError(self.stream_id, err_msg, err_code), self.context.server)
                self.server_state = self.state_errored
            return True

        # Step 3: Do we need to stream this?
        max_stream_size = human.parse_size(self.context.options.stream_large_bodies)
        if max_stream_size is not None and expected_size > max_stream_size:
            if request:
                self.flow.request.stream = True
                if self.request_body_buf:
                    # clear buffer and then fake a DataReceived event with everything we had in the buffer so far.
                    body_buf = self.request_body_buf
                    self.request_body_buf = b""
                    yield from self.start_request_stream()
                    yield from self.handle_event(RequestData(self.stream_id, body_buf))
            if response:
                assert self.flow.response
                self.flow.response.stream = True
                if self.response_body_buf:
                    body_buf = self.response_body_buf
                    self.response_body_buf = b""
                    yield from self.start_response_stream()
                    yield from self.handle_event(ResponseData(self.stream_id, body_buf))
        return False

    def check_killed(self, emit_error_hook: bool) -> layer.CommandGenerator[bool]:
        killed_by_us = (
            self.flow.error and self.flow.error.msg == flow.Error.KILLED_MESSAGE
        )
        # The client may have closed the connection while we were waiting for the hook to complete.
        # We peek into the event queue to see if that is the case.
        killed_by_remote = None
        for evt in self._paused_event_queue:
            if isinstance(evt, RequestProtocolError):
                killed_by_remote = evt.message
                break

        if killed_by_remote:
            if not self.flow.error:
                self.flow.error = flow.Error(killed_by_remote)
        if killed_by_us or killed_by_remote:
            if emit_error_hook:
                yield HttpErrorHook(self.flow)
            # Use the special NO_RESPONSE status code to make sure that no error message is sent to the client.
            yield SendHttp(
                ResponseProtocolError(self.stream_id, "killed", status_codes.NO_RESPONSE),
                self.context.client
            )
            self._handle_event = self.state_errored
            return True
        return False

    def handle_protocol_error(
        self,
        event: Union[RequestProtocolError, ResponseProtocolError]
    ) -> layer.CommandGenerator[None]:
        is_client_error_but_we_already_talk_upstream = (
            isinstance(event, RequestProtocolError)
            and self.client_state in (self.state_stream_request_body, self.state_done)
            and self.server_state not in (self.state_done, self.state_errored)
        )
        need_error_hook = not (
            self.client_state in (self.state_wait_for_request_headers, self.state_errored)
            or
            self.server_state in (self.state_done, self.state_errored)
        )

        if is_client_error_but_we_already_talk_upstream:
            yield SendHttp(event, self.context.server)
            self.client_state = self.state_errored

        if need_error_hook:
            # We don't want to trigger both a response hook and an error hook,
            # so we need to check if the response is done yet or not.
            self.flow.error = flow.Error(event.message)
            yield HttpErrorHook(self.flow)

        if (yield from self.check_killed(False)):
            return

        if isinstance(event, ResponseProtocolError):
            if self.client_state != self.state_errored:
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
        if (yield from self.check_killed(False)):
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
                self.flow.response = http.Response.make(
                    502, f"Cannot connect to {human.format_address(self.context.server.address)}: {err}"
                )
        self.child_layer = layer.NextLayer(self.context)
        yield from self.handle_connect_finish()

    def handle_connect_upstream(self):
        self.child_layer = _upstream_proxy.HttpUpstreamProxy.make(self.context, True)[0]
        yield from self.handle_connect_finish()

    def handle_connect_finish(self):
        if not self.flow.response:
            # Do not send any response headers as it breaks proxying non-80 ports on
            # Android emulators using the -http-proxy option.
            self.flow.response = http.Response(
                self.flow.request.data.http_version,
                200,
                b"Connection established",
                http.Headers(),
                b"",
                None,
                time.time(),
                time.time(),
            )

        if 200 <= self.flow.response.status_code < 300:
            yield SendHttp(ResponseHeaders(self.stream_id, self.flow.response, True), self.context.client)
            yield SendHttp(ResponseEndOfMessage(self.stream_id), self.context.client)
            self.child_layer = self.child_layer or layer.NextLayer(self.context)
            yield from self.child_layer.handle_event(events.Start())
            self._handle_event = self.passthrough
        else:
            yield from self.send_response()

    @expect(RequestData, RequestEndOfMessage, events.Event)
    def passthrough(self, event: events.Event) -> layer.CommandGenerator[None]:
        assert self.flow.response
        assert self.child_layer
        # HTTP events -> normal connection events
        if isinstance(event, RequestData):
            event = events.DataReceived(self.context.client, event.data)
        elif isinstance(event, ResponseData):
            event = events.DataReceived(self.context.server, event.data)
        elif isinstance(event, RequestEndOfMessage):
            event = events.ConnectionClosed(self.context.client)
        elif isinstance(event, ResponseEndOfMessage):
            event = events.ConnectionClosed(self.context.server)

        for command in self.child_layer.handle_event(event):
            # normal connection events -> HTTP events
            if isinstance(command, commands.SendData):
                if command.connection == self.context.client:
                    yield SendHttp(ResponseData(self.stream_id, command.data), self.context.client)
                elif command.connection == self.context.server and self.flow.response.status_code == 101:
                    # there only is a HTTP server connection if we have switched protocols,
                    # not if a connection is established via CONNECT.
                    yield SendHttp(RequestData(self.stream_id, command.data), self.context.server)
                else:
                    yield command
            elif isinstance(command, commands.CloseConnection):
                if command.connection == self.context.client:
                    yield SendHttp(ResponseProtocolError(self.stream_id, "EOF"), self.context.client)
                elif command.connection == self.context.server and self.flow.response.status_code == 101:
                    yield SendHttp(RequestProtocolError(self.stream_id, "EOF"), self.context.server)
                else:
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
    command_sources: Dict[commands.Command, layer.Layer]
    streams: Dict[int, HttpStream]
    connections: Dict[Connection, layer.Layer]
    waiting_for_establishment: DefaultDict[Connection, List[GetHttpConnection]]

    def __init__(self, context: Context, mode: HTTPMode):
        super().__init__(context)
        self.mode = mode

        self.waiting_for_establishment = collections.defaultdict(list)
        self.streams = {}
        self.command_sources = {}

        http_conn: HttpConnection
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
        elif isinstance(event, events.CommandCompleted):
            stream = self.command_sources.pop(event.command)
            yield from self.event_to_child(stream, event)
        elif isinstance(event, events.MessageInjected):
            # For injected messages we pass the HTTP stacks entirely and directly address the stream.
            try:
                conn = self.connections[event.flow.server_conn]
            except KeyError:
                # We have a miss for the server connection, which means we're looking at a connection object
                # that is tunneled over another connection (for example: over an upstream HTTP proxy).
                # We now take the stream associated with the client connection. That won't work for HTTP/2,
                # but it's good enough for HTTP/1.
                conn = self.connections[event.flow.client_conn]
            if isinstance(conn, HttpStream):
                stream_id = conn.stream_id
            else:
                # We reach to the end of the connection's child stack to get the HTTP/1 client layer,
                # which tells us which stream we are dealing with.
                conn = conn.context.layers[-1]
                assert isinstance(conn, Http1Connection)
                assert conn.stream_id
                stream_id = conn.stream_id
            yield from self.event_to_child(self.streams[stream_id], event)
        elif isinstance(event, events.ConnectionEvent):
            if event.connection == self.context.server and self.context.server not in self.connections:
                # We didn't do anything with this connection yet, now the peer is doing something.
                if isinstance(event, events.ConnectionClosed):
                    # The peer has closed it - let's close it too!
                    yield commands.CloseConnection(event.connection)
                elif isinstance(event, events.DataReceived):
                    # The peer has sent data. This can happen with HTTP/2 servers that already send a settings frame.
                    child_layer: HttpConnection
                    if self.context.server.alpn == b"h2":
                        child_layer = Http2Client(self.context.fork())
                    else:
                        child_layer = Http1Client(self.context.fork())
                    self.connections[self.context.server] = child_layer
                    yield from self.event_to_child(child_layer, events.Start())
                    yield from self.event_to_child(child_layer, event)
                else:
                    raise AssertionError(f"Unexpected event: {event}")
            else:
                handler = self.connections[event.connection]
                yield from self.event_to_child(handler, event)
        else:
            raise AssertionError(f"Unexpected event: {event}")

    def event_to_child(
        self,
        child: Union[layer.Layer, HttpStream],
        event: events.Event,
    ) -> layer.CommandGenerator[None]:
        for command in child.handle_event(event):
            assert isinstance(command, commands.Command)
            # Streams may yield blocking commands, which ultimately generate CommandCompleted events.
            # Those need to be routed back to the correct stream, so we need to keep track of that.

            if command.blocking:
                self.command_sources[command] = child

            if isinstance(command, ReceiveHttp):
                if isinstance(command.event, RequestHeaders):
                    yield from self.make_stream(command.event.stream_id)
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

    def make_stream(self, stream_id: int) -> layer.CommandGenerator[None]:
        ctx = self.context.fork()
        self.streams[stream_id] = HttpStream(ctx, stream_id)
        yield from self.event_to_child(self.streams[stream_id], events.Start())

    def get_connection(self, event: GetHttpConnection, *, reuse: bool = True) -> layer.CommandGenerator[None]:
        # Do we already have a connection we can re-use?
        if reuse:
            for connection in self.connections:
                connection_suitable = (
                    event.connection_spec_matches(connection)
                )
                if connection_suitable:
                    if connection in self.waiting_for_establishment:
                        self.waiting_for_establishment[connection].append(event)
                        return
                    elif connection.error:
                        stream = self.command_sources.pop(event)
                        yield from self.event_to_child(stream,
                                                       GetHttpConnectionCompleted(event, (None, connection.error)))
                        return
                    elif connection.connected:
                        # see "tricky multiplexing edge case" in make_http_connection for an explanation
                        h2_to_h1 = self.context.client.alpn == b"h2" and connection.alpn != b"h2"
                        if not h2_to_h1:
                            stream = self.command_sources.pop(event)
                            yield from self.event_to_child(stream,
                                                           GetHttpConnectionCompleted(event, (connection, None)))
                            return
                    else:
                        pass  # the connection is at least half-closed already, we want a new one.

        context_connection_matches = (
            self.context.server not in self.connections and
            event.connection_spec_matches(self.context.server)
        )
        can_use_context_connection = (
            context_connection_matches
            and self.context.server.connected
        )
        if context_connection_matches and self.context.server.error:
            stream = self.command_sources.pop(event)
            yield from self.event_to_child(stream, GetHttpConnectionCompleted(event, (None, self.context.server.error)))
            return

        context = self.context.fork()

        stack = tunnel.LayerStack()

        if not can_use_context_connection:

            context.server = Server(event.address)

            if event.via:
                context.server.via = event.via
                assert event.via.scheme in ("http", "https")
                # We always send a CONNECT request, *except* for plaintext absolute-form HTTP requests in upstream mode.
                send_connect = event.tls or self.mode != HTTPMode.upstream
                stack /= _upstream_proxy.HttpUpstreamProxy.make(context, send_connect)
            if event.tls:
                # Assume that we are in transparent mode and lazily did not open a connection yet.
                # We don't want the IP (which is the address) as the upstream SNI, but the client's SNI instead.
                if self.mode == HTTPMode.transparent and event.address == self.context.server.address:
                    context.server.sni = self.context.client.sni or event.address[0]
                else:
                    context.server.sni = event.address[0]
                stack /= tls.ServerTLSLayer(context)

        stack /= HttpClient(context)

        self.connections[context.server] = stack[0]
        self.waiting_for_establishment[context.server].append(event)

        yield from self.event_to_child(stack[0], events.Start())

    def register_connection(self, command: RegisterHttpConnection) -> layer.CommandGenerator[None]:
        waiting = self.waiting_for_establishment.pop(command.connection)

        reply: Union[Tuple[None, str], Tuple[Connection, None]]
        if command.err:
            reply = (None, command.err)
        else:
            reply = (command.connection, None)

        for cmd in waiting:
            stream = self.command_sources.pop(cmd)
            yield from self.event_to_child(stream, GetHttpConnectionCompleted(cmd, reply))

            # Tricky multiplexing edge case: Assume we are doing HTTP/2 -> HTTP/1 proxying and the destination server
            # only serves responses with HTTP read-until-EOF semantics. In this case we can't process two flows on the
            # same connection. The only workaround left is to open a separate connection for each flow.
            if not command.err and self.context.client.alpn == b"h2" and command.connection.alpn != b"h2":
                for cmd in waiting[1:]:
                    yield from self.get_connection(cmd, reuse=False)
                break


class HttpClient(layer.Layer):
    child_layer: layer.Layer

    @expect(events.Start)
    def _handle_event(self, event: events.Event) -> layer.CommandGenerator[None]:
        err: Optional[str]
        if self.context.server.connected:
            err = None
        else:
            err = yield commands.OpenConnection(self.context.server)
        if not err:
            if self.context.server.alpn == b"h2":
                self.child_layer = Http2Client(self.context)
            else:
                self.child_layer = Http1Client(self.context)
            self._handle_event = self.child_layer.handle_event
            yield from self._handle_event(event)
        yield RegisterHttpConnection(self.context.server, err)
