import asyncio
import logging
import urllib.parse

import asgiref.compatibility
import asgiref.wsgi

from mitmproxy import ctx
from mitmproxy import http

logger = logging.getLogger(__name__)


class ASGIApp:
    """
    An addon that hosts an ASGI/WSGI HTTP app within mitmproxy, at a specified hostname and port.

    Some important caveats:
        - This implementation will block and wait until the entire HTTP response is completed before sending out data.
        - It currently only implements the HTTP protocol (Lifespan and WebSocket are unimplemented).
    """

    def __init__(self, asgi_app, host: str, port: int | None):
        asgi_app = asgiref.compatibility.guarantee_single_callable(asgi_app)
        self.asgi_app, self.host, self.port = asgi_app, host, port

    @property
    def name(self) -> str:
        return f"asgiapp:{self.host}:{self.port}"

    def should_serve(self, flow: http.HTTPFlow) -> bool:
        return bool(
            flow.request.pretty_host == self.host
            and (self.port is None or flow.request.port == self.port)
            and flow.live
            and not flow.error
            and not flow.response
        )

    async def request(self, flow: http.HTTPFlow) -> None:
        if self.should_serve(flow):
            await serve(self.asgi_app, flow)


class WSGIApp(ASGIApp):
    def __init__(self, wsgi_app, host: str, port: int | None):
        asgi_app = asgiref.wsgi.WsgiToAsgi(wsgi_app)
        super().__init__(asgi_app, host, port)


HTTP_VERSION_MAP = {
    "HTTP/1.0": "1.0",
    "HTTP/1.1": "1.1",
    "HTTP/2.0": "2",
}


def make_scope(flow: http.HTTPFlow) -> dict:
    # %3F is a quoted question mark
    quoted_path = urllib.parse.quote_from_bytes(flow.request.data.path).split(
        "%3F", maxsplit=1
    )

    # (Unicode string) – HTTP request target excluding any query string, with percent-encoded
    # sequences and UTF-8 byte sequences decoded into characters.
    path = quoted_path[0]

    # (byte string) – URL portion after the ?, percent-encoded.
    query_string: bytes
    if len(quoted_path) > 1:
        query_string = urllib.parse.unquote(quoted_path[1]).encode()
    else:
        query_string = b""

    return {
        "type": "http",
        "asgi": {
            "version": "3.0",
            "spec_version": "2.1",
        },
        "http_version": HTTP_VERSION_MAP.get(flow.request.http_version, "1.1"),
        "method": flow.request.method,
        "scheme": flow.request.scheme.upper(),
        "path": path,
        "raw_path": flow.request.path,
        "query_string": query_string,
        "headers": [
            (name.lower(), value) for (name, value) in flow.request.headers.fields
        ],
        "client": flow.client_conn.peername,
        "extensions": {
            "mitmproxy.master": ctx.master,
        },
    }


async def serve(app, flow: http.HTTPFlow):
    """
    Serves app on flow.
    """

    scope = make_scope(flow)
    done = asyncio.Event()
    received_body = False
    sent_response = False

    async def receive():
        nonlocal received_body
        if not received_body:
            received_body = True
            return {
                "type": "http.request",
                "body": flow.request.raw_content,
            }
        else:  # pragma: no cover
            # We really don't expect this to be called a second time, but what to do?
            # We just wait until the request is done before we continue here with sending a disconnect.
            await done.wait()
            return {"type": "http.disconnect"}

    async def send(event):
        if event["type"] == "http.response.start":
            flow.response = http.Response.make(
                event["status"], b"", event.get("headers", [])
            )
            flow.response.decode()
        elif event["type"] == "http.response.body":
            assert flow.response
            flow.response.content += event.get("body", b"")
            if not event.get("more_body", False):
                nonlocal sent_response
                sent_response = True
        else:
            raise AssertionError(f"Unexpected event: {event['type']}")

    try:
        await app(scope, receive, send)
        if not sent_response:
            raise RuntimeError(f"no response sent.")
    except Exception as e:
        logger.exception(f"Error in asgi app: {e}")
        flow.response = http.Response.make(500, b"ASGI Error.")
    finally:
        done.set()
