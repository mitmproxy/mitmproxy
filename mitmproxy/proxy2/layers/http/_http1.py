import typing
from abc import abstractmethod

import h11
from h11._readers import ChunkedReader, ContentLengthReader, Http10Reader
from h11._receivebuffer import ReceiveBuffer

from mitmproxy import http
from mitmproxy.net.http import http1
from mitmproxy.net.http.http1 import read_sansio as http1_sansio
from mitmproxy.proxy2 import commands, events
from mitmproxy.proxy2.context import Client, Connection, Server
from mitmproxy.proxy2.layers.http._base import StreamId
from ._base import HttpConnection
from ._events import HttpEvent, RequestData, RequestEndOfMessage, RequestHeaders, ResponseData, ResponseEndOfMessage, \
    ResponseHeaders

TBodyReader = typing.Union[ChunkedReader, Http10Reader, ContentLengthReader]


class Http1Connection(HttpConnection):
    conn: Connection
    stream_id: StreamId = None
    request: http.HTTPRequest
    response: http.HTTPResponse
    state: typing.Callable[[events.Event], typing.Iterator[HttpEvent]]
    body_reader: TBodyReader
    buf: ReceiveBuffer

    def __init__(self, conn: Connection):
        assert isinstance(conn, Connection)
        self.conn = conn
        self.buf = ReceiveBuffer()

    def handle_event(self, event: events.Event) -> typing.Iterator[HttpEvent]:
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

    def wait(self, event: events.Event) -> typing.Iterator[HttpEvent]:
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

    def read_request_headers(self, event: events.Event) -> typing.Iterator[HttpEvent]:
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

    def read_request_body(self, event: events.Event) -> typing.Iterator[HttpEvent]:
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

    def read_response_headers(self, event: events.Event) -> typing.Iterator[HttpEvent]:
        assert isinstance(event, events.ConnectionEvent)
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

    def read_response_body(self, event: events.Event) -> typing.Iterator[HttpEvent]:
        assert isinstance(event, events.ConnectionEvent)
        for e in self.read_body(event, False):
            yield e
            if isinstance(e, ResponseEndOfMessage):
                self.state = self.read_response_headers
                self.stream_id = None
                self.request = None
                self.response = None
                if self.send_queue:
                    send_queue = self.send_queue
                    self.send_queue = []
                    for ev in send_queue:
                        yield from self.send(ev)


__all__ = [
    "Http1Client",
    "Http1Server",
]
