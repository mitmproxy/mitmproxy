from abc import abstractmethod
from queue import Queue
import time
from typing import Dict, Iterable, Optional, Union

from aioquic.h3.connection import (
    H3Connection,
    ErrorCode as H3ErrorCode,
    FrameUnexpected as H3FrameUnexpected,
    Headers as H3Headers,
    HeadersState as H3HeadersState,
)
from aioquic.h3 import events as h3_events
from aioquic.quic import events as quic_events
from aioquic.quic.connection import stream_is_client_initiated, stream_is_unidirectional
from aioquic.quic.packet import QuicErrorCode

from mitmproxy import connection, http, version
from mitmproxy.net.http import status_codes
from mitmproxy.proxy import commands, context, events, layer
from mitmproxy.proxy.layers.quic import (
    QuicStreamDataReceived,
    QuicStreamEvent,
    QuicStreamReset,
    ResetQuicStream,
    SendQuicStreamData,
    error_code_to_str,
    get_connection_error,
    set_connection_error,
)
from mitmproxy.proxy.utils import expect

from . import (
    RequestData,
    RequestEndOfMessage,
    RequestHeaders,
    RequestProtocolError,
    ResponseData,
    ResponseEndOfMessage,
    ResponseHeaders,
    RequestTrailers,
    ResponseTrailers,
    ResponseProtocolError,
)
from ._base import (
    HttpConnection,
    HttpEvent,
    ReceiveHttp,
    format_error,
)
from ._http2 import (
    format_h2_request_headers,
    format_h2_response_headers,
    parse_h2_request_headers,
    parse_h2_response_headers,
)


class MockQuic:
    """
    aioquic intermingles QUIC and HTTP/3. This is something we don't want to do because that makes testing much harder.
    Instead, we mock our QUIC connection object here and then take out the wire data to be sent.
    """

    def __init__(self, conn: connection.Connection, is_client: bool) -> None:
        self.conn = conn
        self.pending_commands: Queue[commands.Command] = Queue()
        self._next_stream_id: list[int, int, int, int] = [0, 1, 2, 3]
        self._is_client = is_client

    def close(
        self,
        error_code: int = QuicErrorCode.NO_ERROR,
        frame_type: Optional[int] = None,
        reason_phrase: str = "",
    ) -> None:
        set_connection_error(self.conn, quic_events.ConnectionTerminated(
            error_code=error_code,
            frame_type=frame_type,
            reason_phrase=reason_phrase,
        ))
        self.pending_commands.put(commands.CloseConnection(self.conn))

    def get_next_available_stream_id(self, is_unidirectional: bool = False) -> int:
        index = (int(is_unidirectional) << 1) | int(not self._is_client)
        stream_id = self._next_stream_id[index]
        self._next_stream_id[index] = stream_id + 4
        return stream_id

    def reset_stream(self, stream_id: int, error_code: int) -> None:
        self.pending_commands.put(ResetQuicStream(self.conn, stream_id, error_code))

    def send_datagram_frame(self, data: bytes) -> None:
        self.pending_commands.put(commands.SendData(self.conn, data))

    def send_stream_data(
        self, stream_id: int, data: bytes, end_stream: bool = False
    ) -> None:
        self.pending_commands.put(SendQuicStreamData(self.conn, stream_id, data, end_stream))

    def stream_can_receive(self, stream_id: int) -> bool:
        return (
            stream_is_client_initiated(stream_id) != self._is_client
            or not stream_is_unidirectional(stream_id)
        )


class LayeredH3Connection(H3Connection):
    def __init__(self, quic: MockQuic, enable_webtransport: bool = False) -> None:
        self._quic = quic
        super().__init__(quic, enable_webtransport)

    def _after_send(self, stream_id: int, end_stream: bool) -> None:
        # if the stream ended, `QuicConnection` has an assert that no further data is being sent
        # to catch this more early on, we set the header state on the `H3Stream`
        if end_stream:
            self._stream[stream_id].headers_send_state = H3HeadersState.AFTER_TRAILERS

    def end_stream(self, stream_id: int) -> None:
        """Ends the given stream."""

        self.send_data(stream_id, data=b"", end_stream=True)

    def get_next_available_stream_id(self, is_unidirectional: bool = False):
        """Reserves and returns the next available stream ID."""

        return self._quic.get_next_available_stream_id(is_unidirectional)

    def has_ended(self, stream_id: int) -> bool:
        """Indicates whether the given stream has been closed by the peer."""

        if not self._quic.stream_can_receive(stream_id):
            return True
        try:
            return self._stream[stream_id].ended
        except KeyError:
            return False

    def has_sent_headers(self, stream_id: int) -> bool:
        """Indicates whether headers have been sent over the given stream."""

        try:
            return self._stream[stream_id].headers_send_state != H3HeadersState.INITIAL
        except KeyError:
            return False

    @property
    def open_stream_ids(self) -> Iterable[int]:
        """Return all streams, that have not been closed by the peer yet."""

        for stream in self._stream.values():
            if self._quic.stream_can_receive(stream.stream_id) and not stream.ended:
                yield stream.stream_id

    def reset_stream(self, stream_id: int, error_code: int) -> None:
        """Resets a stream that hasn't been ended locally yet."""

        # we don't allow reset after FIN
        stream = self._get_or_create_stream(stream_id)
        if stream.headers_send_state == H3HeadersState.AFTER_TRAILERS:
            raise H3FrameUnexpected("reset not allowed in this state")

        # set the header state and queue a reset event
        stream.headers_send_state = H3HeadersState.AFTER_TRAILERS
        self._quic.reset_stream(stream_id, error_code)

    def send_data(self, stream_id: int, data: bytes, end_stream: bool = False) -> None:
        """Sends data over the given stream."""

        super().send_data(stream_id, data, end_stream)
        self._after_send(stream_id, end_stream)

    def send_headers(self, stream_id: int, headers: H3Headers, end_stream: bool = False) -> None:
        """Sends headers over the given stream."""

        # ensure we haven't sent something before
        stream = self._get_or_create_stream(stream_id)
        if stream.headers_send_state != H3HeadersState.INITIAL:
            raise H3FrameUnexpected("initial HEADERS frame is not allowed in this state")
        super().send_headers(stream_id, headers, end_stream)
        self._after_send(stream_id, end_stream)

    def send_trailers(self, stream_id: int, trailers: H3Headers) -> None:
        """Sends trailers over the given stream."""

        # ensure we got some headers first
        stream = self._get_or_create_stream(stream_id)
        if stream.headers_send_state != H3HeadersState.AFTER_HEADERS:
            raise H3FrameUnexpected("trailing HEADERS frame is not allowed in this state")
        super().send_headers(stream_id, trailers, end_stream=True)
        self._after_send(stream_id, end_stream=True)

    def transmit(self) -> layer.CommandGenerator[None]:
        """Yields all pending commands for the upper QUIC layer."""

        while self._quic.pending_commands:
            yield self._quic.pending_commands.get()


class Http3Connection(HttpConnection):
    h3_conn: LayeredH3Connection

    ReceiveData: type[Union[RequestData, ResponseData]]
    ReceiveEndOfMessage: type[Union[RequestEndOfMessage, ResponseEndOfMessage]]
    ReceiveProtocolError: type[Union[RequestProtocolError, ResponseProtocolError]]
    ReceiveTrailers: type[Union[RequestTrailers, ResponseTrailers]]

    def __init__(self, context: context.Context, conn: connection.Connection):
        super().__init__(context, conn)
        self.h3_conn = LayeredH3Connection(MockQuic(self.conn, self.conn is self.context.client))

    @abstractmethod
    def parse_headers(
        self, event: h3_events.HeadersReceived
    ) -> Union[RequestHeaders, ResponseHeaders]:
        pass  # pragma: no cover

    def _handle_event(self, event: events.Event) -> layer.CommandGenerator[None]:
        if isinstance(event, events.Start):
            pass

        # send mitmproxy HTTP events over the H3 connection
        if isinstance(event, HttpEvent):
            try:
                if isinstance(event, (RequestData, ResponseData)):
                    self.h3_conn.send_data(event.stream_id, event.data)
                elif isinstance(event, (RequestHeaders, ResponseHeaders)):
                    headers = yield from (
                        format_h2_request_headers(self.context, event)
                        if isinstance(event, RequestHeaders)
                        else format_h2_response_headers(self.context, event)
                    )
                    self.h3_conn.send_headers(event.stream_id, headers, end_stream=event.end_stream)
                elif isinstance(event, (RequestTrailers, ResponseTrailers)):
                    trailers = [*event.trailers.fields]
                    self.h3_conn.send_trailers(event.stream_id, trailers)
                elif isinstance(event, (RequestEndOfMessage, ResponseEndOfMessage)):
                    self.h3_conn.end_stream(event.stream_id)
                elif isinstance(event, (RequestProtocolError, ResponseProtocolError)):
                    if not self.h3_conn.has_ended(event.stream_id):
                        code = {
                            status_codes.CLIENT_CLOSED_REQUEST: H3ErrorCode.H3_REQUEST_CANCELLED,
                        }.get(event.code, H3ErrorCode.H3_INTERNAL_ERROR)
                        send_error_message = (
                            isinstance(event, ResponseProtocolError)
                            and not self.h3_conn.has_sent_headers(event.stream_id)
                            and event.code != status_codes.NO_RESPONSE
                        )
                        if send_error_message:
                            self.h3_conn.send_headers(
                                event.stream_id,
                                [
                                    (b":status", b"%d" % event.code),
                                    (b"server", version.MITMPROXY.encode()),
                                    (b"content-type", b"text/html"),
                                ],
                            )
                            self.h3_conn.send_data(
                                event.stream_id,
                                format_error(event.code, event.message),
                                end_stream=True,
                            )
                        else:
                            self.h3_conn.reset_stream(event.stream_id, code)
                else:
                    raise AssertionError(f"Unexpected event: {event!r}")

            except H3FrameUnexpected as e:
                # Http2Connection also ignores HttpEvents that violate the current stream state
                yield from commands.Log(f"Received {event!r} unexpectedly: {e}")

            else:
                # transmit buffered data
                yield from self.h3_conn.transmit()

        elif isinstance(event, QuicStreamReset):
            if (
                stream_is_client_initiated(event.stream_id)
                and event.stream_id in self.h3_conn._stream
                and not self.h3_conn._stream[event.stream_id].ended
            ):
                # mark the receiving part of the stream as ended
                # (H3Connection alas doesn't handle StreamReset)
                self.h3_conn._stream[event.stream_id].ended = True

                # report the protocol error (doing the same error code mingling as H2)
                code = (
                    status_codes.CLIENT_CLOSED_REQUEST
                    if event.error_code == H3ErrorCode.H3_REQUEST_CANCELLED
                    else self.ReceiveProtocolError.code
                )
                yield ReceiveHttp(
                    self.ReceiveProtocolError(
                        stream_id=event.stream_id,
                        message=f"stream reset by client ({error_code_to_str(event.error_code)})",
                        code=code,
                    )
                )

        elif isinstance(event, QuicStreamDataReceived):
            yield commands.Log(f"recvd data: {event=}")
            # and convert back...
            e = quic_events.StreamDataReceived(data=event.data, end_stream=event.end_stream, stream_id=event.stream_id)
            for h3_event in self.h3_conn.handle_event(e):
                yield commands.Log(f"{h3_event=}")

                # report received data
                if (
                    isinstance(h3_event, h3_events.DataReceived)
                    and stream_is_client_initiated(h3_event.stream_id)
                ):
                    yield ReceiveHttp(self.ReceiveData(h3_event.stream_id, h3_event.data))
                    if h3_event.stream_ended:
                        yield ReceiveHttp(self.ReceiveEndOfMessage(h3_event.stream_id))

                # report headers and trailers
                elif (
                    isinstance(h3_event, h3_events.HeadersReceived)
                    and stream_is_client_initiated(h3_event.stream_id)
                ):
                    if self.h3_conn._stream[h3_event.stream_id].headers_recv_state is H3HeadersState.AFTER_TRAILERS:
                        trailers = http.Headers(h3_event.headers)
                        yield ReceiveHttp(self.ReceiveTrailers(h3_event.stream_id, trailers))
                    else:
                        try:
                            receive_event = self.parse_headers(h3_event)
                        except ValueError as e:
                            # this will result in a ConnectionClosed event
                            set_connection_error(self.conn, quic_events.ConnectionTerminated(
                                error_code=H3ErrorCode.H3_GENERAL_PROTOCOL_ERROR,
                                frame_type=None,
                                reason_phrase=f"Invalid HTTP/3 request headers: {e}",
                            ))
                            yield commands.CloseConnection(self.conn)
                        else:
                            yield ReceiveHttp(receive_event)

                    # always report an EndOfMessage if the stream has ended
                    if h3_event.stream_ended:
                        yield ReceiveHttp(self.ReceiveEndOfMessage(h3_event.stream_id))

                # we don't support push, web transport, etc.
                else:
                    yield commands.Log(
                        f"Ignored unsupported H3 event: {h3_event!r}",
                        level=(
                            "info"
                            if stream_is_client_initiated(h3_event.stream_id) else
                            "debug"
                        )
                    )

        # report a protocol error for all remaining open streams when a connection is closed
        elif isinstance(event, events.ConnectionClosed):
            close_event = get_connection_error(self.conn)
            msg = (
                "peer closed connection"
                if close_event is None else
                close_event.reason_phrase or error_code_to_str(close_event.error_code)
            )
            for stream_id in self.h3_conn.open_stream_ids:
                yield ReceiveHttp(self.ReceiveProtocolError(stream_id, msg))
            self._handle_event = self.done

        else:
            raise AssertionError(f"Unexpected event: {event!r}")

    @expect(QuicStreamEvent, HttpEvent, events.ConnectionClosed)
    def done(self, _) -> layer.CommandGenerator[None]:
        yield from ()


class Http3Server(Http3Connection):
    ReceiveData = RequestData
    ReceiveEndOfMessage = RequestEndOfMessage
    ReceiveProtocolError = RequestProtocolError
    ReceiveTrailers = RequestTrailers

    def __init__(self, context: context.Context):
        super().__init__(context, context.client)

    def parse_headers(self, event: h3_events.HeadersReceived) -> Union[RequestHeaders, ResponseHeaders]:
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

    def __init__(self, context: context.Context):
        super().__init__(context, context.server)
        self.our_stream_id: Dict[int, int] = {}
        self.their_stream_id: Dict[int, int] = {}

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

    def parse_headers(self, event: h3_events.HeadersReceived) -> Union[RequestHeaders, ResponseHeaders]:
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
