import html
import textwrap
from dataclasses import dataclass

from mitmproxy import http
from mitmproxy.connection import Connection
from mitmproxy.proxy import commands
from mitmproxy.proxy import events
from mitmproxy.proxy import layer
from mitmproxy.proxy.context import Context

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


def format_error(status_code: int, message: str) -> bytes:
    reason = http.status_codes.RESPONSES.get(status_code, "Unknown")
    return (
        textwrap.dedent(
            f"""
    <html>
    <head>
        <title>{status_code} {reason}</title>
    </head>
    <body>
        <h1>{status_code} {reason}</h1>
        <p>{html.escape(message)}</p>
    </body>
    </html>
    """
        )
        .strip()
        .encode("utf8", "replace")
    )
