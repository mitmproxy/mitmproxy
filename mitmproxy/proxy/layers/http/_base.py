import html
import textwrap
from dataclasses import dataclass

import h2.utilities

from mitmproxy import ctx, http
from mitmproxy.connection import Connection
from mitmproxy.proxy import commands, events, layer
from mitmproxy.proxy.context import Context
from mitmproxy.proxy.layers.http import RequestHeaders, ResponseHeaders

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


def get_request_headers(
    event: RequestHeaders,
) -> layer.CommandGenerator[list[tuple[bytes, bytes]]]:
    pseudo_headers = [
        (b":method", event.request.data.method),
        (b":scheme", event.request.data.scheme),
        (b":path", event.request.data.path),
    ]
    if event.request.authority:
        pseudo_headers.append((b":authority", event.request.data.authority))

    if event.request.is_http2 or event.request.is_http3:
        hdrs = list(event.request.headers.fields)
        if ctx.options.normalize_outbound_headers:
            yield from normalize_h2_or_h3_headers(hdrs)
    else:
        headers = event.request.headers
        if not event.request.authority and "host" in headers:
            headers = headers.copy()
            pseudo_headers.append((b":authority", headers.pop(b"host")))
        hdrs = normalize_h1_headers(list(headers.fields), True)

    return pseudo_headers + hdrs


def get_response_headers(
    event: ResponseHeaders,
) -> layer.CommandGenerator[list[tuple[bytes, bytes]]]:
    headers = [
        (b":status", b"%d" % event.response.status_code),
        *event.response.headers.fields,
    ]
    if event.response.is_http2 or event.request.is_http3:
        if ctx.options.normalize_outbound_headers:
            yield from normalize_h2_or_h3_headers(headers)
    else:
        headers = normalize_h1_headers(headers, False)
    return headers


def normalize_h1_headers(
    headers: list[tuple[bytes, bytes]], is_client: bool
) -> list[tuple[bytes, bytes]]:
    # HTTP/1 servers commonly send capitalized headers (Content-Length vs content-length),
    # which isn't valid HTTP/2 or HTTP/3. As such we normalize.
    headers = h2.utilities.normalize_outbound_headers(
        headers,
        h2.utilities.HeaderValidationFlags(is_client, False, not is_client, False),
    )
    # make sure that this is not just an iterator but an iterable,
    # otherwise hyper-h2 will silently drop headers.
    headers = list(headers)
    return headers


def normalize_h2_or_h3_headers(
    headers: list[tuple[bytes, bytes]]
) -> layer.CommandGenerator[None]:
    for i in range(len(headers)):
        if not headers[i][0].islower():
            yield commands.Log(
                f"Lowercased {repr(headers[i][0]).lstrip('b')} header as uppercase is not allowed with HTTP/2 nor HTTP/3."
            )
            headers[i] = (headers[i][0].lower(), headers[i][1])
