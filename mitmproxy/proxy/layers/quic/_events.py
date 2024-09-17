from __future__ import annotations

from dataclasses import dataclass

from mitmproxy import connection
from mitmproxy.proxy import events


@dataclass
class QuicStreamEvent(events.ConnectionEvent):
    """Base class for all QUIC stream events."""

    stream_id: int
    """The ID of the stream the event was fired for."""


@dataclass
class QuicStreamDataReceived(QuicStreamEvent):
    """Event that is fired whenever data is received on a stream."""

    data: bytes
    """The data which was received."""
    end_stream: bool
    """Whether the STREAM frame had the FIN bit set."""

    def __repr__(self):
        target = repr(self.connection).partition("(")[0].lower()
        end_stream = "[end_stream] " if self.end_stream else ""
        return f"QuicStreamDataReceived({target} on {self.stream_id}, {end_stream}{self.data!r})"


@dataclass
class QuicStreamReset(QuicStreamEvent):
    """Event that is fired when the remote peer resets a stream."""

    error_code: int
    """The error code that triggered the reset."""


@dataclass
class QuicStreamStopSending(QuicStreamEvent):
    """Event that is fired when the remote peer sends a STOP_SENDING frame."""

    error_code: int
    """The application protocol error code."""


class QuicConnectionClosed(events.ConnectionClosed):
    """QUIC connection has been closed."""

    error_code: int
    "The error code which was specified when closing the connection."

    frame_type: int | None
    "The frame type which caused the connection to be closed, or `None`."

    reason_phrase: str
    "The human-readable reason for which the connection was closed."

    def __init__(
        self,
        conn: connection.Connection,
        error_code: int,
        frame_type: int | None,
        reason_phrase: str,
    ) -> None:
        super().__init__(conn)
        self.error_code = error_code
        self.frame_type = frame_type
        self.reason_phrase = reason_phrase
