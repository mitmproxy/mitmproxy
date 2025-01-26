from __future__ import annotations

from mitmproxy import connection
from mitmproxy.proxy import commands


class QuicStreamCommand(commands.ConnectionCommand):
    """Base class for all QUIC stream commands."""

    stream_id: int
    """The ID of the stream the command was issued for."""

    def __init__(self, connection: connection.Connection, stream_id: int) -> None:
        super().__init__(connection)
        self.stream_id = stream_id


class SendQuicStreamData(QuicStreamCommand):
    """Command that sends data on a stream."""

    data: bytes
    """The data which should be sent."""
    end_stream: bool
    """Whether the FIN bit should be set in the STREAM frame."""

    def __init__(
        self,
        connection: connection.Connection,
        stream_id: int,
        data: bytes,
        end_stream: bool = False,
    ) -> None:
        super().__init__(connection, stream_id)
        self.data = data
        self.end_stream = end_stream

    def __repr__(self):
        target = repr(self.connection).partition("(")[0].lower()
        end_stream = "[end_stream] " if self.end_stream else ""
        return f"SendQuicStreamData({target} on {self.stream_id}, {end_stream}{self.data!r})"


class ResetQuicStream(QuicStreamCommand):
    """Abruptly terminate the sending part of a stream."""

    error_code: int
    """An error code indicating why the stream is being reset."""

    def __init__(
        self, connection: connection.Connection, stream_id: int, error_code: int
    ) -> None:
        super().__init__(connection, stream_id)
        self.error_code = error_code


class StopSendingQuicStream(QuicStreamCommand):
    """Request termination of the receiving part of a stream."""

    error_code: int
    """An error code indicating why the stream is being stopped."""

    def __init__(
        self, connection: connection.Connection, stream_id: int, error_code: int
    ) -> None:
        super().__init__(connection, stream_id)
        self.error_code = error_code


class CloseQuicConnection(commands.CloseConnection):
    """Close a QUIC connection."""

    error_code: int
    "The error code which was specified when closing the connection."

    frame_type: int | None
    "The frame type which caused the connection to be closed, or `None`."

    reason_phrase: str
    "The human-readable reason for which the connection was closed."

    # XXX: A bit much boilerplate right now. Should switch to dataclasses.
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
