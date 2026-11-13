from collections.abc import Iterable
from dataclasses import dataclass

from aioquic.h3.connection import H3Connection
from aioquic.h3.connection import H3Event
from aioquic.h3.connection import Headers
from aioquic.h3.events import HeadersReceived
from aioquic.h3.exceptions import InvalidStreamStateError
from aioquic.quic.configuration import QuicConfiguration
from aioquic.quic.connection import stream_is_unidirectional
from aioquic.quic.events import StreamDataReceived
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
class TrailersReceived(H3Event):
    """
    The TrailersReceived event is fired whenever trailers are received.
    """

    trailers: Headers
    "The trailers."

    stream_id: int
    "The ID of the stream the trailers were received for."

    stream_ended: bool
    "Whether the STREAM frame had the FIN bit set."


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
    aioquic intermingles QUIC and HTTP/3. This is something we don't want to do because that makes testing much harder.
    Instead, we mock our QUIC connection object here and then take out the wire data to be sent.
    """

    def __init__(self, conn: connection.Connection, is_client: bool) -> None:
        self.conn = conn
        self.pending_commands: list[commands.Command] = []
        self._next_stream_id: list[int] = [0, 1, 2, 3]
        self._is_client = is_client
        self.closed = False
        """Whether close() was called, by H3Connection or by us."""

        # the following fields are accessed by H3Connection
        self.configuration = QuicConfiguration(is_client=is_client)
        self._quic_logger = None

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
        self.closed = True
        self.pending_commands.append(
            CloseQuicConnection(self.conn, error_code, frame_type, reason_phrase)
        )

    def get_next_available_stream_id(self, is_unidirectional: bool = False) -> int:
        # since we always reserve the ID, we have to "find" the next ID like `QuicConnection` does
        index = (int(is_unidirectional) << 1) | int(not self._is_client)
        stream_id = self._next_stream_id[index]
        self._next_stream_id[index] = stream_id + 4
        return stream_id

    def reset_stream(self, stream_id: int, error_code: int) -> None:
        self.pending_commands.append(ResetQuicStream(self.conn, stream_id, error_code))

    def stop_send(self, stream_id: int, error_code: int) -> None:
        self.pending_commands.append(
            StopSendingQuicStream(self.conn, stream_id, error_code)
        )

    def send_stream_data(
        self, stream_id: int, data: bytes, end_stream: bool = False
    ) -> None:
        self.pending_commands.append(
            SendQuicStreamData(self.conn, stream_id, data, end_stream)
        )


@dataclass
class _StreamState:
    """The state of a request stream, as seen by mitmproxy."""

    headers_received: bool = False
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
        self._closed_streams: set[int] = set()
        """
        We keep track of all stream IDs for which we have requested
        STOP_SENDING to silently discard incoming data.
        """
        self._streams: dict[int, _StreamState] = {}
        """
        aioquic forgets about streams once they have ended,
        so we keep track of request streams ourselves.

        Unlike aioquic, we never forget a stream, as we need its state to reject
        sends after it ended. This grows with the number of requests made on the
        connection, like `_closed_streams`.
        """
        super().__init__(self._mock)  # type: ignore

    @property
    def _closed(self) -> bool:
        """Whether either side closed the connection, so incoming events are ignored."""
        # H3Connection closes the connection itself on protocol errors
        return self._connection_closed or self._mock.closed

    def _stream_state(self, stream_id: int) -> _StreamState:
        try:
            return self._streams[stream_id]
        except KeyError:
            state = self._streams[stream_id] = _StreamState()
            return state

    def _report_trailers(self, events: list[H3Event]) -> list[H3Event]:
        """Turns HeadersReceived into TrailersReceived for trailers."""

        for index, event in enumerate(events):
            if isinstance(event, HeadersReceived):
                state = self._stream_state(event.stream_id)
                if state.headers_received:
                    events[index] = TrailersReceived(
                        event.headers, event.stream_id, event.stream_ended
                    )
                elif not any(
                    name == b":status" and value.startswith(b"1")
                    for name, value in event.headers
                ):
                    # interim (1xx) responses come before the final headers
                    state.headers_received = True
        return events

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

    def get_next_available_stream_id(self, is_unidirectional: bool = False):
        """Reserves and returns the next available stream ID."""

        return self._mock.get_next_available_stream_id(is_unidirectional)

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
            self.close_stream(
                event.stream_id,
                event.error_code,
                stop_send=isinstance(event, QuicStreamStopSending),
            )
            self._stream_state(event.stream_id).recv_ended = True
            return [StreamClosed(event.stream_id, event.error_code)]

        # convert data events from the QUIC layer back to aioquic events
        elif isinstance(event, QuicStreamDataReceived):
            # Discard contents if we have already sent STOP_SENDING on this stream.
            if event.stream_id in self._closed_streams:
                return []
            if not stream_is_unidirectional(event.stream_id):
                self._stream_state(event.stream_id).recv_ended = event.end_stream
            # QPACK can also report a request stream's headers while handling its
            # encoder stream, once they are no longer blocked
            return self._report_trailers(
                self.handle_event(
                    StreamDataReceived(event.data, event.end_stream, event.stream_id)
                )
            )

        # should never happen
        else:  # pragma: no cover
            raise AssertionError(f"Unexpected event: {event!r}")

    def has_sent_headers(self, stream_id: int) -> bool:
        """Indicates whether headers have been sent over the given stream."""

        state = self._streams.get(stream_id)
        return state is not None and (state.headers_sent or state.send_ended)

    def close_stream(
        self, stream_id: int, error_code: int, stop_send: bool = True
    ) -> None:
        """Close a stream that hasn't been closed locally yet."""
        if stream_id not in self._closed_streams:
            self._closed_streams.add(stream_id)
            self._stream_state(stream_id).send_ended = True
            # https://www.rfc-editor.org/rfc/rfc9000.html#section-3.5-8
            # An endpoint that wishes to terminate both directions of
            # a bidirectional stream can terminate one direction by
            # sending a RESET_STREAM frame, and it can encourage prompt
            # termination in the opposite direction by sending a
            # STOP_SENDING frame.
            self._mock.reset_stream(stream_id=stream_id, error_code=error_code)
            if stop_send:
                self._mock.stop_send(stream_id=stream_id, error_code=error_code)

    def send_data(self, stream_id: int, data: bytes, end_stream: bool = False) -> None:
        """Sends data over the given stream."""

        # aioquic forgets streams once they have ended, so catch this early on.
        state = self._stream_state(stream_id)
        if state.send_ended:
            raise InvalidStreamStateError("DATA frame is not allowed in this state")
        super().send_data(stream_id, data, end_stream)
        state.send_ended = end_stream

    def send_datagram(self, flow_id: int, data: bytes) -> None:
        # supporting datagrams would require additional information from the underlying QUIC connection
        raise NotImplementedError()  # pragma: no cover

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

    def transmit(self) -> layer.CommandGenerator[None]:
        """Yields all pending commands for the upper QUIC layer."""

        while self._mock.pending_commands:
            yield self._mock.pending_commands.pop(0)


__all__ = [
    "LayeredH3Connection",
    "StreamClosed",
    "TrailersReceived",
]
