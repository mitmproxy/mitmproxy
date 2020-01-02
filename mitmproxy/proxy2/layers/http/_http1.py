import abc
import typing

import h11
from h11._readers import ChunkedReader, ContentLengthReader, Http10Reader
from h11._receivebuffer import ReceiveBuffer

from mitmproxy import http
from mitmproxy.net.http import http1
from mitmproxy.net.http.http1 import read_sansio as http1_sansio
from mitmproxy.proxy2 import commands, events, layer
from mitmproxy.proxy2.context import Client, Connection, Context, Server
from mitmproxy.proxy2.layers.http._base import ReceiveHttp, StreamId
from mitmproxy.proxy2.utils import expect
from mitmproxy.utils import human
from ._base import HttpConnection
from ._events import HttpEvent, RequestData, RequestEndOfMessage, RequestHeaders, RequestProtocolError, ResponseData, \
    ResponseEndOfMessage, ResponseHeaders, ResponseProtocolError

TBodyReader = typing.Union[ChunkedReader, Http10Reader, ContentLengthReader]


class Http1Connection(HttpConnection, metaclass=abc.ABCMeta):
    conn: Connection
    stream_id: typing.Optional[StreamId] = None
    request: typing.Optional[http.HTTPRequest] = None
    response: typing.Optional[http.HTTPResponse] = None
    request_done: bool = False
    response_done: bool = False
    state: typing.Callable[[events.Event], layer.CommandGenerator[None]]
    body_reader: TBodyReader
    buf: ReceiveBuffer

    def __init__(self, context: Context, conn: Connection):
        super().__init__(context)
        assert isinstance(conn, Connection)
        self.conn = conn
        self.buf = ReceiveBuffer()

    def _handle_event(self, event: events.Event) -> layer.CommandGenerator[None]:
        if isinstance(event, HttpEvent):
            yield from self.send(event)
        else:
            if isinstance(event, events.DataReceived):
                self.buf += event.data
            yield from self.state(event)

    @abc.abstractmethod
    def send(self, event: HttpEvent) -> layer.CommandGenerator[None]:
        yield from ()

    def make_body_reader(self, expected_size: typing.Optional[int]) -> TBodyReader:
        if expected_size is None:
            return ChunkedReader()
        elif expected_size == -1:
            return Http10Reader()
        else:
            return ContentLengthReader(expected_size)

    def read_body(self, event: events.Event, is_request: bool) -> layer.CommandGenerator[None]:
        while True:
            try:
                if isinstance(event, events.DataReceived):
                    h11_event = self.body_reader(self.buf)
                elif isinstance(event, events.ConnectionClosed):
                    h11_event = self.body_reader.read_eof()
                else:
                    raise ValueError(f"Unexpected event: {event}")
            except h11.ProtocolError as e:
                yield commands.CloseConnection(self.conn)
                if is_request:
                    yield ReceiveHttp(RequestProtocolError(self.stream_id, str(e)))
                else:
                    yield ReceiveHttp(ResponseProtocolError(self.stream_id, str(e)))
                return

            if h11_event is None:
                return
            elif isinstance(h11_event, h11.Data):
                h11_event.data: bytearray  # type checking
                if is_request:
                    yield ReceiveHttp(RequestData(self.stream_id, bytes(h11_event.data)))
                else:
                    yield ReceiveHttp(ResponseData(self.stream_id, bytes(h11_event.data)))
            elif isinstance(h11_event, h11.EndOfMessage):
                if is_request:
                    yield ReceiveHttp(RequestEndOfMessage(self.stream_id))
                else:
                    yield ReceiveHttp(ResponseEndOfMessage(self.stream_id))
                return

    def wait(self, event: events.Event) -> layer.CommandGenerator[None]:
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

    def __init__(self, context: Context):
        super().__init__(context, context.client)
        self.stream_id = 1
        self.state = self.read_request_headers

    def send(self, event: HttpEvent) -> layer.CommandGenerator[None]:
        assert event.stream_id == self.stream_id
        if isinstance(event, ResponseHeaders):
            self.response = event.response
            raw = http1.assemble_response_head(event.response)
            yield commands.SendData(self.conn, raw)
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
            yield commands.SendData(self.conn, raw)
        elif isinstance(event, ResponseEndOfMessage):
            if "chunked" in self.response.headers.get("transfer-encoding", "").lower():
                yield commands.SendData(self.conn, b"0\r\n\r\n")
            elif http1.expected_http_body_size(self.request, self.response) == -1 or self.request.first_line_format == "authority":
                yield commands.CloseConnection(self.conn)
            yield from self.mark_done(response=True)
        elif isinstance(event, ResponseProtocolError):
            if not self.response:
                resp = http.make_error_response(event.code, event.message)
                raw = http1.assemble_response(resp)
                yield commands.SendData(self.conn, raw)
            yield commands.CloseConnection(self.conn)
        else:
            raise NotImplementedError(f"{event}")

    def mark_done(self, *, request: bool = False, response: bool = False) -> layer.CommandGenerator[None]:
        if request:
            self.request_done = True
        if response:
            self.response_done = True
        if self.request_done and self.response_done:
            self.request_done = self.response_done = False
            self.request = self.response = None
            self.stream_id += 2
            self.state = self.read_request_headers
            yield from self.state(events.DataReceived(self.conn, b""))
        elif self.request_done:
            self.state = self.wait

    def read_request_headers(self, event: events.Event) -> layer.CommandGenerator[None]:
        if isinstance(event, events.DataReceived):
            request_head = self.buf.maybe_extract_lines()
            if request_head:
                request_head = [bytes(x) for x in request_head]  # TODO: Make url.parse compatible with bytearrays
                try:
                    self.request = http.HTTPRequest.wrap(http1_sansio.read_request_head(request_head))
                except ValueError as e:
                    yield commands.Log(f"{human.format_address(self.conn.address)}: {e}")
                    yield commands.CloseConnection(self.conn)
                    self.state = self.wait
                    return
                yield ReceiveHttp(RequestHeaders(self.stream_id, self.request))

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
            else:
                pass  # FIXME: protect against header size DoS
        elif isinstance(event, events.ConnectionClosed):
            if bytes(self.buf).strip():
                yield commands.Log(f"Client closed connection before sending request headers: {bytes(self.buf)}")
                yield commands.Log(f"Receive Buffer: {bytes(self.buf)}", level="debug")
            yield commands.CloseConnection(self.conn)
        else:
            raise ValueError(f"Unexpected event: {event}")

    def read_request_body(self, event: events.Event) -> layer.CommandGenerator[None]:
        for e in self.read_body(event, True):
            yield e
            if isinstance(e, ReceiveHttp) and isinstance(e.event, RequestEndOfMessage):
                yield from self.mark_done(request=True)


class Http1Client(Http1Connection):
    conn: Server
    send_queue: typing.List[HttpEvent]
    """A queue of send events for flows other than the one that is currently being transmitted."""

    def __init__(self, context: Context):
        super().__init__(context, context.server)
        self.state = self.read_response_headers
        self.send_queue = []

    def send(self, event: HttpEvent) -> layer.CommandGenerator[None]:
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
            yield commands.SendData(self.conn, raw)
        elif isinstance(event, RequestData):
            if "chunked" in self.request.headers.get("transfer-encoding", "").lower():
                raw = b"%x\r\n%s\r\n" % (len(event.data), event.data)
            else:
                raw = event.data
            yield commands.SendData(self.conn, raw)
        elif isinstance(event, RequestEndOfMessage):
            if "chunked" in self.request.headers.get("transfer-encoding", "").lower():
                yield commands.SendData(self.conn, b"0\r\n\r\n")
            elif http1.expected_http_body_size(self.request) == -1:
                assert not self.send_queue
                yield commands.CloseConnection(self.conn)
            yield from self.mark_done(request=True)
        elif isinstance(event, RequestProtocolError):
            yield commands.CloseConnection(self.conn)
            return
        else:
            raise NotImplementedError(f"{event}")

    def mark_done(self, *, request: bool = False, response: bool = False) -> layer.CommandGenerator[None]:
        if request:
            self.request_done = True
        if response:
            self.response_done = True
        if self.request_done and self.response_done:
            self.request_done = self.response_done = False
            self.request = self.response = None
            self.stream_id = None
            if self.send_queue:
                send_queue = self.send_queue
                self.send_queue = []
                for ev in send_queue:
                    yield from self.send(ev)

    @expect(events.ConnectionEvent)
    def read_response_headers(self, event: events.ConnectionEvent) -> layer.CommandGenerator[None]:
        if isinstance(event, events.DataReceived):
            response_head = self.buf.maybe_extract_lines()

            if response_head:
                response_head = [bytes(x) for x in response_head]
                self.response = http.HTTPResponse.wrap(http1_sansio.read_response_head(response_head))
                yield ReceiveHttp(ResponseHeaders(self.stream_id, self.response))

                expected_size = http1.expected_http_body_size(self.request, self.response)
                self.body_reader = self.make_body_reader(expected_size)

                self.state = self.read_response_body
                yield from self.state(event)
            else:
                pass  # FIXME: protect against header size DoS
        elif isinstance(event, events.ConnectionClosed):
            if self.stream_id:
                if self.buf:
                    yield ReceiveHttp(
                        ResponseProtocolError(self.stream_id, f"unexpected server response: {bytes(self.buf)}"))
                else:
                    # The server has closed the connection to prevent us from continuing.
                    # We need to signal that to the stream.
                    # https://tools.ietf.org/html/rfc7231#section-6.5.11
                    yield ReceiveHttp(ResponseProtocolError(self.stream_id, "server closed connection"))
            else:
                return
            yield commands.CloseConnection(self.conn)
        else:
            raise ValueError(f"Unexpected event: {event}")

    @expect(events.ConnectionEvent)
    def read_response_body(self, event: events.ConnectionEvent) -> layer.CommandGenerator[None]:
        for e in self.read_body(event, False):
            yield e
            if isinstance(e, ReceiveHttp) and isinstance(e.event, ResponseEndOfMessage):
                self.state = self.read_response_headers
                yield from self.mark_done(response=True)


__all__ = [
    "Http1Client",
    "Http1Server",
]
