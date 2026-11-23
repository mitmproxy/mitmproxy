from collections.abc import Iterable
from dataclasses import dataclass

from aioquic.h3.connection import H3Connection
from aioquic.h3.connection import H3Event
from aioquic.h3.connection import Headers
from aioquic.h3.exceptions import InvalidStreamStateError
from aioquic.quic.configuration import QuicConfiguration
from aioquic.quic.connection import stream_is_client_initiated
from aioquic.quic.connection import stream_is_unidirectional
from aioquic.quic.events import StopSendingReceived
from aioquic.quic.events import StreamDataReceived
from aioquic.quic.events import StreamReset
from aioquic.quic.packet import QuicErrorCode

from mitmproxy import connection
from mitmproxy.proxy import commands
from mitmproxy.proxy import layer
from mitmproxy.proxy.layers.quic import CloseQuicConnection
from mitmproxy.proxy.layers.quic import QuicConnectionClosed
from mitmproxy.proxy.layers.quic import QuicStreamDataReceived
from mitmproxy.proxy.layers.quic import QuicStreamEvent
from mitmproxy.proxy.layers.quic import QuicStreamReset
from mitmproxy.proxy.layers.quic import QuicStreamStopSending
from mitmproxy.proxy.layers.quic import ResetQuicStream
from mitmproxy.proxy.layers.quic import SendQuicStreamData
from mitmproxy.proxy.layers.quic import StopSendingQuicStream


@dataclass
class StreamClosed(H3Event):
    """
    The StreamReset event is fired when the peer is sending a CLOSE_STREAM
    or a STOP_SENDING frame. For HTTP/3, we don't differentiate between the two.
    """

    stream_id: int
    "The ID of the stream that was reset."

    error_code: int
    """The error code indicating why the stream was closed."""


class MockQuic:
    """
    H3Connection sends by calling methods of a QuicConnection. In mitmproxy, the QuicConnection
    belongs to the QUIC layer, so this class stands in for it and turns those calls into commands
    for that layer.

    Its public methods are the ones of `QuicConnection` which H3Connection uses, with the same
    semantics. Its only other public member is `pending_commands`, which holds what it sends.
    Anything else mitmproxy needs belongs in `LayeredH3Connection`.
    """

    def __init__(self, conn: connection.Connection, is_client: bool) -> None:
        self.pending_commands: list[commands.Command] = []
        """The commands for the QUIC layer, in place of what QuicConnection would send."""
        self._closed = False
        self._conn = conn
        self._is_client = is_client
        self._next_stream_id: list[int] = [0, 1, 2, 3]
        """Per stream type, the first stream ID nothing was sent on yet."""

        # the following fields are accessed by H3Connection
        self.configuration = QuicConfiguration(is_client=is_client)
        self._quic_logger = None

    def can_send_stream_data(self, stream_id: int) -> bool:
        # LayeredH3Connection checks the stream state itself before sending
        return True

    def close(
        self,
        error_code: int = QuicErrorCode.NO_ERROR,
        frame_type: int | None = None,
        reason_phrase: str = "",
    ) -> None:
        # we'll get closed if a protocol error occurs in `H3Connection.handle_event`
        # we note the error on the connection and yield a CloseConnection
        # this will then call `QuicConnection.close` with the proper values
        # once the `Http3Connection` receives `ConnectionClosed`, it will send out `ProtocolError`
        self._closed = True
        self.pending_commands.append(
            CloseQuicConnection(self._conn, error_code, frame_type, reason_phrase)
        )

    def get_next_available_stream_id(self, is_unidirectional: bool = False) -> int:
        # like `QuicConnection`, a stream ID is only used once something is sent on it
        return self._next_stream_id[self._stream_type(is_unidirectional)]

    def is_closing(self) -> bool:
        return self._closed

    def reset_stream(self, stream_id: int, error_code: int) -> None:
        self._use_stream(stream_id)
        self.pending_commands.append(ResetQuicStream(self._conn, stream_id, error_code))

    def send_stream_data(
        self, stream_id: int, data: bytes, end_stream: bool = False
    ) -> None:
        self._use_stream(stream_id)
        self.pending_commands.append(
            SendQuicStreamData(self._conn, stream_id, data, end_stream)
        )

    def stop_stream(self, stream_id: int, error_code: int) -> None:
        self._use_stream(stream_id)
        self.pending_commands.append(
            StopSendingQuicStream(self._conn, stream_id, error_code)
        )

    def _stream_type(self, is_unidirectional: bool) -> int:
        """Returns the index of our streams of the given direction."""
        return (int(is_unidirectional) << 1) | int(not self._is_client)

    def _use_stream(self, stream_id: int) -> None:
        """Like `QuicConnection`, sending on one of our streams also opens those before it."""
        if stream_is_client_initiated(stream_id) == self._is_client:
            index = self._stream_type(stream_is_unidirectional(stream_id))
            self._next_stream_id[index] = max(
                self._next_stream_id[index], stream_id + 4
            )


@dataclass
class _StreamState:
    """The state of a request stream, as seen by mitmproxy."""

    headers_sent: bool = False
    send_ended: bool = False
    recv_ended: bool = False


class LayeredH3Connection(H3Connection):
    """
    Creates a H3 connection using a fake QUIC connection, which allows layer separation.
    Also ensures that headers, data and trailers are sent in that order.
    """

    def __init__(self, conn: connection.Connection, is_client: bool) -> None:
        self._mock = MockQuic(conn, is_client)
        self._connection_closed = False
        """Whether the QUIC layer reported that the connection was closed."""
        self._next_reserved_stream_id = self._mock.get_next_available_stream_id()
        """The first request stream ID `reserve_stream_id` has not returned yet."""
        self._streams: dict[int, _StreamState] = {}
        """
        aioquic forgets about streams once they have ended,
        so we keep track of request streams ourselves.

        Unlike aioquic, we never forget a stream, as we need its state to reject
        sends after it ended. This grows with the number of requests made on the
        connection.
        """
        super().__init__(self._mock)  # type: ignore

    @property
    def _closed(self) -> bool:
        """Whether either side closed the connection, so incoming events are ignored."""
        # H3Connection closes the connection itself on protocol errors
        return self._connection_closed or self._mock.is_closing()

    def _stream_state(self, stream_id: int) -> _StreamState:
        try:
            return self._streams[stream_id]
        except KeyError:
            state = self._streams[stream_id] = _StreamState()
            return state

    def close_connection(
        self,
        error_code: int = QuicErrorCode.NO_ERROR,
        frame_type: int | None = None,
        reason_phrase: str = "",
    ) -> None:
        """Closes the underlying QUIC connection and ignores any incoming events."""

        self._mock.close(error_code, frame_type, reason_phrase)

    def end_stream(self, stream_id: int) -> None:
        """Ends the given stream if not already done so."""

        state = self._stream_state(stream_id)
        if not state.send_ended:
            super().send_data(stream_id, b"", end_stream=True)
            state.send_ended = True

    def get_open_stream_ids(self) -> Iterable[int]:
        """Iterates over all non-special open streams"""

        return (
            stream_id
            for stream_id, state in self._streams.items()
            if not (state.send_ended and state.recv_ended)
        )

    def handle_connection_closed(self, event: QuicConnectionClosed) -> None:
        self._connection_closed = True

    def handle_stream_event(self, event: QuicStreamEvent) -> list[H3Event]:
        # don't do anything if we're done
        if self._closed:
            return []

        elif isinstance(event, (QuicStreamReset, QuicStreamStopSending)):
            # Let aioquic know which direction the peer terminated. It closes the
            # connection if this is a critical stream, and it reports nothing
            # we need, since we report StreamClosed instead.
            if isinstance(event, QuicStreamReset):
                self.handle_event(StreamReset(event.error_code, event.stream_id))
            else:
                self.handle_event(
                    StopSendingReceived(event.error_code, event.stream_id)
                )
            if self._closed or not (
                stream_is_client_initiated(event.stream_id)
                and not stream_is_unidirectional(event.stream_id)
            ):
                return []

            # The peer gave up on the request, so we terminate what is still open.
            self.terminate_request(event.stream_id, error_code=event.error_code)
            return [StreamClosed(event.stream_id, event.error_code)]

        # convert data events from the QUIC layer back to aioquic events
        elif isinstance(event, QuicStreamDataReceived):
            # aioquic drops data on streams that were terminated
            if not stream_is_unidirectional(event.stream_id):
                state = self._stream_state(event.stream_id)
                if event.end_stream:
                    state.recv_ended = True
            return self.handle_event(
                StreamDataReceived(event.data, event.end_stream, event.stream_id)
            )

        # should never happen
        else:  # pragma: no cover
            raise AssertionError(f"Unexpected event: {event!r}")

    def has_sent_headers(self, stream_id: int) -> bool:
        """Indicates whether headers have been sent over the given stream."""

        state = self._streams.get(stream_id)
        return state is not None and (state.headers_sent or state.send_ended)

    def reserve_stream_id(self) -> int:
        """
        Reserves and returns the ID of a new request stream, which no other call
        returns, even if nothing was sent on the previous ones yet.
        """

        stream_id = max(
            self._mock.get_next_available_stream_id(), self._next_reserved_stream_id
        )
        self._next_reserved_stream_id = stream_id + 4
        return stream_id

    def send_data(self, stream_id: int, data: bytes, end_stream: bool = False) -> None:
        """Sends data over the given stream."""

        # aioquic forgets streams once they have ended, so catch this early on.
        state = self._stream_state(stream_id)
        if state.send_ended:
            raise InvalidStreamStateError("DATA frame is not allowed in this state")
        super().send_data(stream_id, data, end_stream)
        state.send_ended = end_stream

    def send_headers(
        self, stream_id: int, headers: Headers, end_stream: bool = False
    ) -> None:
        """Sends headers over the given stream."""

        # ensure we haven't sent something before
        state = self._stream_state(stream_id)
        if state.headers_sent or state.send_ended:
            raise InvalidStreamStateError(
                "initial HEADERS frame is not allowed in this state"
            )
        super().send_headers(stream_id, headers, end_stream)
        state.headers_sent = True
        state.send_ended = end_stream

    def send_trailers(self, stream_id: int, trailers: Headers) -> None:
        """Sends trailers over the given stream and ends it."""

        # ensure we got some headers first
        state = self._stream_state(stream_id)
        if not state.headers_sent or state.send_ended:
            raise InvalidStreamStateError(
                "trailing HEADERS frame is not allowed in this state"
            )
        super().send_headers(stream_id, trailers, end_stream=True)
        state.send_ended = True

    def terminate_request(
        self, stream_id: int, *, error_code: int | None = None
    ) -> None:
        """Terminates the directions of a request stream which are still open."""

        try:
            super().terminate_request(stream_id, error_code=error_code)
        except InvalidStreamStateError:
            # we reserved this stream but sent nothing on it, so nothing is open
            pass
        state = self._stream_state(stream_id)
        state.send_ended = True
        state.recv_ended = True

    def transmit(self) -> layer.CommandGenerator[None]:
        """Yields all pending commands for the upper QUIC layer."""

        while self._mock.pending_commands:
            yield self._mock.pending_commands.pop(0)


__all__ = [
    "LayeredH3Connection",
    "StreamClosed",
]
