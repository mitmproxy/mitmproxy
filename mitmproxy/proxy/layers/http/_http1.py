import abc
from collections.abc import Callable
from typing import Union

import h11
from h11._readers import ChunkedReader
from h11._readers import ContentLengthReader
from h11._readers import Http10Reader
from h11._receivebuffer import ReceiveBuffer

from ...context import Context
from ._base import format_error
from ._base import HttpConnection
from ._events import HttpEvent
from ._events import RequestData
from ._events import RequestEndOfMessage
from ._events import RequestHeaders
from ._events import RequestProtocolError
from ._events import ResponseData
from ._events import ResponseEndOfMessage
from ._events import ResponseHeaders
from ._events import ResponseProtocolError
from mitmproxy import http
from mitmproxy import version
from mitmproxy.connection import Connection
from mitmproxy.connection import ConnectionState
from mitmproxy.net.http import http1
from mitmproxy.net.http import status_codes
from mitmproxy.proxy import commands
from mitmproxy.proxy import events
from mitmproxy.proxy import layer
from mitmproxy.proxy.layers.http._base import ReceiveHttp
from mitmproxy.proxy.layers.http._base import StreamId
from mitmproxy.proxy.utils import expect
from mitmproxy.utils import human

TBodyReader = Union[ChunkedReader, Http10Reader, ContentLengthReader]


class Http1Connection(HttpConnection, metaclass=abc.ABCMeta):
    stream_id: StreamId | None = None
    request: http.Request | None = None
    response: http.Response | None = None
    request_done: bool = False
    response_done: bool = False
    # this is a bit of a hack to make both mypy and PyCharm happy.
    state: Callable[[events.Event], layer.CommandGenerator[None]] | Callable
    body_reader: TBodyReader
    buf: ReceiveBuffer

    ReceiveProtocolError: type[RequestProtocolError | ResponseProtocolError]
    ReceiveData: type[RequestData | ResponseData]
    ReceiveEndOfMessage: type[RequestEndOfMessage | ResponseEndOfMessage]

    def __init__(self, context: Context, conn: Connection):
        super().__init__(context, conn)
        self.buf = ReceiveBuffer()

    @abc.abstractmethod
    def send(self, event: HttpEvent) -> layer.CommandGenerator[None]:
        yield from ()  # pragma: no cover

    @abc.abstractmethod
    def read_headers(
        self, event: events.ConnectionEvent
    ) -> layer.CommandGenerator[None]:
        yield from ()  # pragma: no cover

    def _handle_event(self, event: events.Event) -> layer.CommandGenerator[None]:
        if isinstance(event, HttpEvent):
            yield from self.send(event)
        else:
            if (
                isinstance(event, events.DataReceived)
                and self.state != self.passthrough
            ):
                self.buf += event.data
            yield from self.state(event)

    @expect(events.Start)
    def start(self, _) -> layer.CommandGenerator[None]:
        self.state = self.read_headers
        yield from ()

    state = start

    def read_body(self, event: events.Event) -> layer.CommandGenerator[None]:
        assert self.stream_id is not None
        while True:
            try:
                if isinstance(event, events.DataReceived):
                    h11_event = self.body_reader(self.buf)
                elif isinstance(event, events.ConnectionClosed):
                    h11_event = self.body_reader.read_eof()
                else:
                    raise AssertionError(f"Unexpected event: {event}")
            except h11.ProtocolError as e:
                yield commands.CloseConnection(self.conn)
                yield ReceiveHttp(
                    self.ReceiveProtocolError(
                        self.stream_id, f"HTTP/1 protocol error: {e}"
                    )
                )
                return

            if h11_event is None:
                return
            elif isinstance(h11_event, h11.Data):
                data: bytes = bytes(h11_event.data)
                if data:
                    yield ReceiveHttp(self.ReceiveData(self.stream_id, data))
            elif isinstance(h11_event, h11.EndOfMessage):
                assert self.request
                if h11_event.headers:
                    raise NotImplementedError(f"HTTP trailers are not implemented yet.")
                if self.request.data.method.upper() != b"CONNECT":
                    yield ReceiveHttp(self.ReceiveEndOfMessage(self.stream_id))
                is_request = isinstance(self, Http1Server)
                yield from self.mark_done(request=is_request, response=not is_request)
                return

    def wait(self, event: events.Event) -> layer.CommandGenerator[None]:
        """
        We wait for the current flow to be finished before parsing the next message,
        as we may want to upgrade to WebSocket or plain TCP before that.
        """
        assert self.stream_id
        if isinstance(event, events.DataReceived):
            return
        elif isinstance(event, events.ConnectionClosed):
            # for practical purposes, we assume that a peer which sent at least a FIN
            # is not interested in any more data from us, see
            # see https://github.com/httpwg/http-core/issues/22
            if event.connection.state is not ConnectionState.CLOSED:
                yield commands.CloseConnection(event.connection)
            yield ReceiveHttp(
                self.ReceiveProtocolError(
                    self.stream_id,
                    f"Client disconnected.",
                    code=status_codes.CLIENT_CLOSED_REQUEST,
                )
            )
        else:  # pragma: no cover
            raise AssertionError(f"Unexpected event: {event}")

    def done(self, event: events.ConnectionEvent) -> layer.CommandGenerator[None]:
        yield from ()  # pragma: no cover

    def make_pipe(self) -> layer.CommandGenerator[None]:
        self.state = self.passthrough
        if self.buf:
            already_received = self.buf.maybe_extract_at_most(len(self.buf)) or b""
            # Some clients send superfluous newlines after CONNECT, we want to eat those.
            already_received = already_received.lstrip(b"\r\n")
            if already_received:
                yield from self.state(events.DataReceived(self.conn, already_received))

    def passthrough(self, event: events.Event) -> layer.CommandGenerator[None]:
        assert self.stream_id
        if isinstance(event, events.DataReceived):
            yield ReceiveHttp(self.ReceiveData(self.stream_id, event.data))
        elif isinstance(event, events.ConnectionClosed):
            if isinstance(self, Http1Server):
                yield ReceiveHttp(RequestEndOfMessage(self.stream_id))
            else:
                yield ReceiveHttp(ResponseEndOfMessage(self.stream_id))

    def mark_done(
        self, *, request: bool = False, response: bool = False
    ) -> layer.CommandGenerator[None]:
        if request:
            self.request_done = True
        if response:
            self.response_done = True
        if self.request_done and self.response_done:
            assert self.request
            assert self.response
            if should_make_pipe(self.request, self.response):
                yield from self.make_pipe()
                return
            try:
                read_until_eof_semantics = (
                    http1.expected_http_body_size(self.request, self.response) == -1
                )
            except ValueError:
                # this may raise only now (and not earlier) because an addon set invalid headers,
                # in which case it's not really clear what we are supposed to do.
                read_until_eof_semantics = False
            connection_done = (
                read_until_eof_semantics
                or http1.connection_close(
                    self.request.http_version, self.request.headers
                )
                or http1.connection_close(
                    self.response.http_version, self.response.headers
                )
                # If we proxy HTTP/2 to HTTP/1, we only use upstream connections for one request.
                # This simplifies our connection management quite a bit as we can rely on
                # the proxyserver's max-connection-per-server throttling.
                or (
                    (self.request.is_http2 or self.request.is_http3)
                    and isinstance(self, Http1Client)
                )
            )
            if connection_done:
                yield commands.CloseConnection(self.conn)
                self.state = self.done
                return
            self.request_done = self.response_done = False
            self.request = self.response = None
            if isinstance(self, Http1Server):
                self.stream_id += 2
            else:
                self.stream_id = None
            self.state = self.read_headers
            if self.buf:
                yield from self.state(events.DataReceived(self.conn, b""))


class Http1Server(Http1Connection):
    """A simple HTTP/1 server with no pipelining support."""

    ReceiveProtocolError = RequestProtocolError
    ReceiveData = RequestData
    ReceiveEndOfMessage = RequestEndOfMessage
    stream_id: int

    def __init__(self, context: Context):
        super().__init__(context, context.client)
        self.stream_id = 1

    def send(self, event: HttpEvent) -> layer.CommandGenerator[None]:
        assert event.stream_id == self.stream_id
        if isinstance(event, ResponseHeaders):
            self.response = response = event.response

            if response.is_http2 or response.is_http3:
                response = response.copy()
                # Convert to an HTTP/1 response.
                response.http_version = "HTTP/1.1"
                # not everyone supports empty reason phrases, so we better make up one.
                response.reason = status_codes.RESPONSES.get(response.status_code, "")
                # Shall we set a Content-Length header here if there is none?
                # For now, let's try to modify as little as possible.

            raw = http1.assemble_response_head(response)
            yield commands.SendData(self.conn, raw)
        elif isinstance(event, ResponseData):
            assert self.response
            if "chunked" in self.response.headers.get("transfer-encoding", "").lower():
                raw = b"%x\r\n%s\r\n" % (len(event.data), event.data)
            else:
                raw = event.data
            if raw:
                yield commands.SendData(self.conn, raw)
        elif isinstance(event, ResponseEndOfMessage):
            assert self.request
            assert self.response
            if (
                self.request.method.upper() != "HEAD"
                and "chunked"
                in self.response.headers.get("transfer-encoding", "").lower()
            ):
                yield commands.SendData(self.conn, b"0\r\n\r\n")
            yield from self.mark_done(response=True)
        elif isinstance(event, ResponseProtocolError):
            if not self.response and event.code != status_codes.NO_RESPONSE:
                yield commands.SendData(
                    self.conn, make_error_response(event.code, event.message)
                )
            if self.conn.state & ConnectionState.CAN_WRITE:
                yield commands.CloseConnection(self.conn)
        else:
            raise AssertionError(f"Unexpected event: {event}")

    def read_headers(
        self, event: events.ConnectionEvent
    ) -> layer.CommandGenerator[None]:
        if isinstance(event, events.DataReceived):
            request_head = self.buf.maybe_extract_lines()
            if request_head:
                try:
                    self.request = http1.read_request_head(
                        [bytes(x) for x in request_head]
                    )
                    if self.context.options.validate_inbound_headers:
                        http1.validate_headers(self.request.headers)
                    expected_body_size = http1.expected_http_body_size(self.request)
                except ValueError as e:
                    yield commands.SendData(self.conn, make_error_response(400, str(e)))
                    yield commands.CloseConnection(self.conn)
                    if self.request:
                        # we have headers that we can show in the ui
                        yield ReceiveHttp(
                            RequestHeaders(self.stream_id, self.request, False)
                        )
                        yield ReceiveHttp(
                            RequestProtocolError(self.stream_id, str(e), 400)
                        )
                    else:
                        yield commands.Log(
                            f"{human.format_address(self.conn.peername)}: {e}"
                        )
                    self.state = self.done
                    return
                yield ReceiveHttp(
                    RequestHeaders(
                        self.stream_id, self.request, expected_body_size == 0
                    )
                )
                self.body_reader = make_body_reader(expected_body_size)
                self.state = self.read_body
                yield from self.state(event)
            else:
                pass  # FIXME: protect against header size DoS
        elif isinstance(event, events.ConnectionClosed):
            buf = bytes(self.buf)
            if buf.strip():
                yield commands.Log(
                    f"Client closed connection before completing request headers: {buf!r}"
                )
            yield commands.CloseConnection(self.conn)
        else:
            raise AssertionError(f"Unexpected event: {event}")

    def mark_done(
        self, *, request: bool = False, response: bool = False
    ) -> layer.CommandGenerator[None]:
        yield from super().mark_done(request=request, response=response)
        if self.request_done and not self.response_done:
            self.state = self.wait


class Http1Client(Http1Connection):
    """A simple HTTP/1 client with no pipelining support."""

    ReceiveProtocolError = ResponseProtocolError
    ReceiveData = ResponseData
    ReceiveEndOfMessage = ResponseEndOfMessage

    def __init__(self, context: Context):
        super().__init__(context, context.server)

    def send(self, event: HttpEvent) -> layer.CommandGenerator[None]:
        if isinstance(event, RequestProtocolError):
            yield commands.CloseConnection(self.conn)
            return

        if self.stream_id is None:
            assert isinstance(event, RequestHeaders)
            self.stream_id = event.stream_id
            self.request = event.request
        assert self.stream_id == event.stream_id

        if isinstance(event, RequestHeaders):
            request = event.request
            if request.is_http2 or request.is_http3:
                # Convert to an HTTP/1 request.
                request = (
                    request.copy()
                )  # (we could probably be a bit more efficient here.)
                request.http_version = "HTTP/1.1"
                if "Host" not in request.headers and request.authority:
                    request.headers.insert(0, "Host", request.authority)
                request.authority = ""
                cookie_headers = request.headers.get_all("Cookie")
                if len(cookie_headers) > 1:
                    # Only HTTP/2 supports multiple cookie headers, HTTP/1.x does not.
                    # see: https://www.rfc-editor.org/rfc/rfc6265#section-5.4
                    #      https://www.rfc-editor.org/rfc/rfc7540#section-8.1.2.5
                    request.headers["Cookie"] = "; ".join(cookie_headers)
            raw = http1.assemble_request_head(request)
            yield commands.SendData(self.conn, raw)
        elif isinstance(event, RequestData):
            assert self.request
            if "chunked" in self.request.headers.get("transfer-encoding", "").lower():
                raw = b"%x\r\n%s\r\n" % (len(event.data), event.data)
            else:
                raw = event.data
            if raw:
                yield commands.SendData(self.conn, raw)
        elif isinstance(event, RequestEndOfMessage):
            assert self.request
            if "chunked" in self.request.headers.get("transfer-encoding", "").lower():
                yield commands.SendData(self.conn, b"0\r\n\r\n")
            elif http1.expected_http_body_size(self.request, self.response) == -1:
                yield commands.CloseTcpConnection(self.conn, half_close=True)
            yield from self.mark_done(request=True)
        else:
            raise AssertionError(f"Unexpected event: {event}")

    def read_headers(
        self, event: events.ConnectionEvent
    ) -> layer.CommandGenerator[None]:
        if isinstance(event, events.DataReceived):
            if not self.request:
                # we just received some data for an unknown request.
                yield commands.Log(f"Unexpected data from server: {bytes(self.buf)!r}")
                yield commands.CloseConnection(self.conn)
                return
            assert self.stream_id is not None

            response_head = self.buf.maybe_extract_lines()
            if response_head:
                try:
                    self.response = http1.read_response_head(
                        [bytes(x) for x in response_head]
                    )
                    if self.context.options.validate_inbound_headers:
                        http1.validate_headers(self.response.headers)
                    expected_size = http1.expected_http_body_size(
                        self.request, self.response
                    )
                except ValueError as e:
                    yield commands.CloseConnection(self.conn)
                    yield ReceiveHttp(
                        ResponseProtocolError(
                            self.stream_id, f"Cannot parse HTTP response: {e}"
                        )
                    )
                    return
                yield ReceiveHttp(
                    ResponseHeaders(self.stream_id, self.response, expected_size == 0)
                )
                self.body_reader = make_body_reader(expected_size)

                self.state = self.read_body
                yield from self.state(event)
            else:
                pass  # FIXME: protect against header size DoS
        elif isinstance(event, events.ConnectionClosed):
            if self.conn.state & ConnectionState.CAN_WRITE:
                yield commands.CloseConnection(self.conn)
            if self.stream_id:
                if self.buf:
                    yield ReceiveHttp(
                        ResponseProtocolError(
                            self.stream_id,
                            f"unexpected server response: {bytes(self.buf)!r}",
                        )
                    )
                else:
                    # The server has closed the connection to prevent us from continuing.
                    # We need to signal that to the stream.
                    # https://tools.ietf.org/html/rfc7231#section-6.5.11
                    yield ReceiveHttp(
                        ResponseProtocolError(
                            self.stream_id, "server closed connection"
                        )
                    )
            else:
                return
        else:
            raise AssertionError(f"Unexpected event: {event}")


def should_make_pipe(request: http.Request, response: http.Response) -> bool:
    if response.status_code == 101:
        return True
    elif response.status_code == 200 and request.method.upper() == "CONNECT":
        return True
    else:
        return False


def make_body_reader(expected_size: int | None) -> TBodyReader:
    if expected_size is None:
        return ChunkedReader()
    elif expected_size == -1:
        return Http10Reader()
    else:
        return ContentLengthReader(expected_size)


def make_error_response(
    status_code: int,
    message: str = "",
) -> bytes:
    resp = http.Response.make(
        status_code,
        format_error(status_code, message),
        http.Headers(
            Server=version.MITMPROXY,
            Connection="close",
            Content_Type="text/html",
        ),
    )
    return http1.assemble_response(resp)


__all__ = [
    "Http1Client",
    "Http1Server",
]
