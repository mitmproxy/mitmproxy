from dataclasses import dataclass

from mitmproxy.proxy import events, layer, commands
from mitmproxy.proxy.context import Connection, Context

StreamId = int


@dataclass
class HttpEvent(events.Event):
    # we need stream ids on every event to avoid race conditions
    stream_id: StreamId


class HttpConnection(layer.Layer):
    conn: Connection

    def __init__(self, context: Context, conn: Connection):
        super().__init__(context)
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
