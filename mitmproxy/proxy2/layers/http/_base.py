from dataclasses import dataclass

from mitmproxy.proxy2 import events, layer, commands
from mitmproxy.proxy2.context import Connection, Context

StreamId = int


@dataclass
class HttpEvent(events.Event):
    # we need stream ids on every event to avoid race conditions
    stream_id: StreamId

    def __repr__(self) -> str:
        x = self.__dict__.copy()
        x.pop("stream_id")
        return f"{type(self).__name__}({repr(x) if x else ''})"


class HttpConnection(layer.Layer):
    conn: Connection

    def __init__(self, context: Context, conn: Connection):
        super().__init__(context)
        assert isinstance(conn, Connection)
        self.conn = conn


class HttpCommand(commands.Command):
    pass


class ReceiveHttp(HttpCommand):
    event: HttpEvent

    def __init__(self, event: HttpEvent):
        self.event = event

    def __repr__(self) -> str:
        return f"Receive({self.event})"


__all__ = [
    "HttpConnection",
    "StreamId",
    "HttpEvent",
]
