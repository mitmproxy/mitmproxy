import time
from abc import abstractmethod
from logging import DEBUG
from logging import WARNING
from typing import assert_never

from aioquic.h3.connection import ErrorCode as H3ErrorCode
from aioquic.h3.events import DataReceived
from aioquic.h3.events import GoAwayReceived
from aioquic.h3.events import HeadersReceived
from aioquic.h3.exceptions import InvalidStreamStateError

from . import ErrorCode
from . import RequestData
from . import RequestEndOfMessage
from . import RequestHeaders
from . import RequestProtocolError
from . import RequestTrailers
from . import ResponseData
from . import ResponseEndOfMessage
from . import ResponseHeaders
from . import ResponseProtocolError
from . import ResponseTrailers
from ._base import format_error
from ._base import HttpConnection
from ._base import HttpEvent
from ._base import ReceiveHttp
from ._http2 import format_h2_request_headers
from ._http2 import format_h2_response_headers
from ._http2 import parse_h2_request_headers
from ._http2 import parse_h2_response_headers
from ._http_h3 import LayeredH3Connection
from ._http_h3 import StreamClosed
from ._http_h3 import TrailersReceived
from mitmproxy import connection
from mitmproxy import http
from mitmproxy import version
from mitmproxy.net.http import status_codes
from mitmproxy.proxy import commands
from mitmproxy.proxy import context
from mitmproxy.proxy import events
from mitmproxy.proxy import layer
from mitmproxy.proxy.layers.quic import error_code_to_str
from mitmproxy.proxy.layers.quic import QuicConnectionClosed
from mitmproxy.proxy.layers.quic import QuicStreamEvent
from mitmproxy.proxy.utils import expect


class Http3Connection(HttpConnection):
    h3_conn: LayeredH3Connection

    ReceiveData: type[RequestData | ResponseData]
    ReceiveEndOfMessage: type[RequestEndOfMessage | ResponseEndOfMessage]
    ReceiveProtocolError: type[RequestProtocolError | ResponseProtocolError]
    ReceiveTrailers: type[RequestTrailers | ResponseTrailers]

    def __init__(self, context: context.Context, conn: connection.Connection):
        super().__init__(context, conn)
        self.h3_conn = LayeredH3Connection(
            self.conn, is_client=self.conn is self.context.server
        )

    def _handle_event(self, event: events.Event) -> layer.CommandGenerator[None]:
        if isinstance(event, events.Start):
            yield from self.h3_conn.transmit()

        # send mitmproxy HTTP events over the H3 connection
        elif isinstance(event, HttpEvent):
            try:
                if isinstance(event, (RequestData, ResponseData)):
                    self.h3_conn.send_data(event.stream_id, event.data)
                elif isinstance(event, (RequestHeaders, ResponseHeaders)):
                    headers = yield from (
                        format_h2_request_headers(self.context, event)
                        if isinstance(event, RequestHeaders)
                        else format_h2_response_headers(self.context, event)
                    )
                    try:
                        self.h3_conn.send_headers(
                            event.stream_id, headers, end_stream=event.end_stream
                        )
                    except ValueError as e:
                        yield from self.fail_unencodable_stream(event, e)
                elif isinstance(event, (RequestTrailers, ResponseTrailers)):
                    try:
                        self.h3_conn.send_trailers(
                            event.stream_id, [*event.trailers.fields]
                        )
                    except ValueError as e:
                        yield from self.fail_unencodable_stream(event, e)
                elif isinstance(event, (RequestEndOfMessage, ResponseEndOfMessage)):
                    self.h3_conn.end_stream(event.stream_id)
                elif isinstance(event, (RequestProtocolError, ResponseProtocolError)):
                    status = event.code.http_status_code()
                    if (
                        isinstance(event, ResponseProtocolError)
                        and not self.h3_conn.has_sent_headers(event.stream_id)
                        and status is not None
                    ):
                        self.send_error_response(event.stream_id, status, event.message)
                    else:
                        match event.code:
                            case ErrorCode.CANCEL | ErrorCode.CLIENT_DISCONNECTED:
                                error_code = H3ErrorCode.H3_REQUEST_CANCELLED
                            case ErrorCode.KILL:
                                error_code = H3ErrorCode.H3_INTERNAL_ERROR
                            case ErrorCode.HTTP_1_1_REQUIRED:
                                error_code = H3ErrorCode.H3_VERSION_FALLBACK
                            case ErrorCode.PASSTHROUGH_CLOSE:
                                # FIXME: This probably shouldn't be a protocol error, but an EOM event.
                                error_code = H3ErrorCode.H3_REQUEST_CANCELLED
                            case (
                                ErrorCode.GENERIC_CLIENT_ERROR
                                | ErrorCode.GENERIC_SERVER_ERROR
                                | ErrorCode.REQUEST_TOO_LARGE
                                | ErrorCode.RESPONSE_TOO_LARGE
                                | ErrorCode.CONNECT_FAILED
                                | ErrorCode.DESTINATION_UNKNOWN
                                | ErrorCode.REQUEST_VALIDATION_FAILED
                                | ErrorCode.RESPONSE_VALIDATION_FAILED
                            ):
                                error_code = H3ErrorCode.H3_INTERNAL_ERROR
                            case other:  # pragma: no cover
                                assert_never(other)
                        self.h3_conn.close_stream(event.stream_id, error_code.value)
                else:  # pragma: no cover
                    raise AssertionError(f"Unexpected event: {event!r}")

            except InvalidStreamStateError as e:
                # Http2Connection also ignores HttpEvents that violate the current stream state
                yield commands.Log(f"Received {event!r} unexpectedly: {e}")

            except (ValueError, RuntimeError) as e:
                yield commands.Log(f"Failed to encode HTTP/3 data for {event!r}: {e}")
                self.h3_conn.close_stream(
                    event.stream_id,
                    H3ErrorCode.H3_INTERNAL_ERROR.value,
                )
                yield from self.h3_conn.transmit()

            else:
                # transmit buffered data
                yield from self.h3_conn.transmit()

        # forward stream messages from the QUIC layer to the H3 connection
        elif isinstance(event, QuicStreamEvent):
            h3_events = self.h3_conn.handle_stream_event(event)
            for h3_event in h3_events:
                if isinstance(h3_event, StreamClosed):
                    err_str = error_code_to_str(h3_event.error_code)
                    match h3_event.error_code:
                        case H3ErrorCode.H3_REQUEST_CANCELLED:
                            err_code = ErrorCode.CANCEL
                        case H3ErrorCode.H3_VERSION_FALLBACK:
                            err_code = ErrorCode.HTTP_1_1_REQUIRED
                        case _:
                            err_code = self.ReceiveProtocolError.code
                    yield ReceiveHttp(
                        self.ReceiveProtocolError(
                            h3_event.stream_id,
                            f"stream closed by client ({err_str})",
                            code=err_code,
                        )
                    )
                elif isinstance(h3_event, DataReceived):
                    if h3_event.data:
                        yield ReceiveHttp(
                            self.ReceiveData(h3_event.stream_id, h3_event.data)
                        )
                    if h3_event.stream_ended:
                        yield ReceiveHttp(self.ReceiveEndOfMessage(h3_event.stream_id))
                elif isinstance(h3_event, HeadersReceived):
                    try:
                        receive_event = self.parse_headers(h3_event)
                    except ValueError as e:
                        self.h3_conn.close_connection(
                            error_code=H3ErrorCode.H3_GENERAL_PROTOCOL_ERROR,
                            reason_phrase=f"Invalid HTTP/3 request headers: {e}",
                        )
                    else:
                        if (
                            isinstance(receive_event, ResponseHeaders)
                            and 100 <= receive_event.response.status_code < 200
                        ):
                            # Like for HTTP/2, we violate the spec here and don't forward
                            # 1xx responses, see Http2Client for the rationale.
                            status = receive_event.response.status_code
                            reason = status_codes.RESPONSES.get(status, "")
                            yield commands.Log(
                                f"Swallowing HTTP/3 informational response: {status} {reason}"
                            )
                            continue
                        yield ReceiveHttp(receive_event)
                        if h3_event.stream_ended:
                            yield ReceiveHttp(
                                self.ReceiveEndOfMessage(h3_event.stream_id)
                            )
                elif isinstance(h3_event, TrailersReceived):
                    yield ReceiveHttp(
                        self.ReceiveTrailers(
                            h3_event.stream_id, http.Headers(h3_event.trailers)
                        )
                    )
                    if h3_event.stream_ended:
                        yield ReceiveHttp(self.ReceiveEndOfMessage(h3_event.stream_id))
                elif isinstance(h3_event, GoAwayReceived):
                    # Unlike Http2Client, which closes the connection on GOAWAY, we keep it
                    # open so that requests the server has started to process complete.
                    # We lack a mechanism to stop reusing a connection, so the server will
                    # reject any later requests.
                    yield commands.Log(
                        f"HTTP/3 server is shutting down, it will not process "
                        f"stream {h3_event.stream_id} and above.",
                        DEBUG,
                    )
                else:  # pragma: no cover
                    raise AssertionError(f"Unexpected event: {event!r}")
            yield from self.h3_conn.transmit()

        # report a protocol error for all remaining open streams when a connection is closed
        elif isinstance(event, QuicConnectionClosed):
            self._handle_event = self.done  # type: ignore
            self.h3_conn.handle_connection_closed(event)
            msg = event.reason_phrase or error_code_to_str(event.error_code)
            for stream_id in self.h3_conn.get_open_stream_ids():
                yield ReceiveHttp(
                    self.ReceiveProtocolError(
                        stream_id, msg, self.ReceiveProtocolError.code
                    )
                )

        else:  # pragma: no cover
            raise AssertionError(f"Unexpected event: {event!r}")

    def send_error_response(self, stream_id: int, status: int, message: str) -> None:
        """Answer a request with an error page, which ends the stream."""
        self.h3_conn.send_headers(
            stream_id,
            [
                (b":status", b"%d" % status),
                (b"server", version.MITMPROXY.encode()),
                (b"content-type", b"text/html"),
            ],
        )
        self.h3_conn.send_data(
            stream_id, format_error(status, message), end_stream=True
        )

    def fail_unencodable_stream(
        self,
        event: RequestHeaders | ResponseHeaders | RequestTrailers | ResponseTrailers,
        err: ValueError,
    ) -> layer.CommandGenerator[None]:
        """
        Fail a stream whose headers or trailers QPACK cannot encode.

        ls-qpack refuses a header name or value longer than 65,535 bytes.
        HTTP/2 and HTTP/3 peers cannot send these, as both limit received headers
        to 64 KiB, but addons, modify_headers or replayed flows can produce them.
        Nothing has been sent for these headers, and the encoder stays usable.
        """
        msg = f"Cannot encode HTTP/3 headers: {err}"
        # The flow only records an error if the response is not complete yet,
        # so make sure that this does not go unnoticed.
        yield commands.Log(msg, WARNING)
        if isinstance(event, ResponseHeaders):
            # Nothing has reached the client yet, so tell it what went wrong.
            self.send_error_response(event.stream_id, status_codes.BAD_GATEWAY, msg)
        else:
            self.h3_conn.close_stream(
                event.stream_id, H3ErrorCode.H3_INTERNAL_ERROR.value
            )
        yield from self.h3_conn.transmit()
        yield ReceiveHttp(
            self.ReceiveProtocolError(
                event.stream_id, msg, code=self.ReceiveProtocolError.code
            )
        )

    @expect(HttpEvent, QuicStreamEvent, QuicConnectionClosed)
    def done(self, _) -> layer.CommandGenerator[None]:
        yield from ()

    @abstractmethod
    def parse_headers(self, event: HeadersReceived) -> RequestHeaders | ResponseHeaders:
        pass  # pragma: no cover


class Http3Server(Http3Connection):
    ReceiveData = RequestData
    ReceiveEndOfMessage = RequestEndOfMessage
    ReceiveProtocolError = RequestProtocolError
    ReceiveTrailers = RequestTrailers

    def __init__(self, context: context.Context):
        super().__init__(context, context.client)

    def parse_headers(self, event: HeadersReceived) -> RequestHeaders | ResponseHeaders:
        # same as HTTP/2
        (
            host,
            port,
            method,
            scheme,
            authority,
            path,
            headers,
        ) = parse_h2_request_headers(event.headers)
        request = http.Request(
            host=host,
            port=port,
            method=method,
            scheme=scheme,
            authority=authority,
            path=path,
            http_version=b"HTTP/3",
            headers=headers,
            content=None,
            trailers=None,
            timestamp_start=time.time(),
            timestamp_end=None,
        )
        return RequestHeaders(event.stream_id, request, end_stream=event.stream_ended)


class Http3Client(Http3Connection):
    ReceiveData = ResponseData
    ReceiveEndOfMessage = ResponseEndOfMessage
    ReceiveProtocolError = ResponseProtocolError
    ReceiveTrailers = ResponseTrailers

    our_stream_id: dict[int, int]
    their_stream_id: dict[int, int]

    def __init__(self, context: context.Context):
        super().__init__(context, context.server)
        self.our_stream_id = {}
        self.their_stream_id = {}

    def _handle_event(self, event: events.Event) -> layer.CommandGenerator[None]:
        # QUIC and HTTP/3 would actually allow for direct stream ID mapping, but since we want
        # to support H2<->H3, we need to translate IDs.
        # NOTE: We always create bidirectional streams, as we can't safely infer unidirectionality.
        if isinstance(event, HttpEvent):
            ours = self.our_stream_id.get(event.stream_id, None)
            if ours is None:
                ours = self.h3_conn.get_next_available_stream_id()
                self.our_stream_id[event.stream_id] = ours
                self.their_stream_id[ours] = event.stream_id
            event.stream_id = ours

        for cmd in super()._handle_event(event):
            if isinstance(cmd, ReceiveHttp):
                cmd.event.stream_id = self.their_stream_id[cmd.event.stream_id]
            yield cmd

    def parse_headers(self, event: HeadersReceived) -> RequestHeaders | ResponseHeaders:
        # same as HTTP/2
        status_code, headers = parse_h2_response_headers(event.headers)
        response = http.Response(
            http_version=b"HTTP/3",
            status_code=status_code,
            reason=b"",
            headers=headers,
            content=None,
            trailers=None,
            timestamp_start=time.time(),
            timestamp_end=None,
        )
        return ResponseHeaders(event.stream_id, response, event.stream_ended)


__all__ = [
    "Http3Client",
    "Http3Server",
]
