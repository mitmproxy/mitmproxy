#!/usr/bin/env python3
"""Generate a flow file with one sample flow per type and state mitmweb can display.

    python test/helper_tools/gen_sample_flows.py      # writes sample-flows.mitm
    mitmweb -r sample-flows.mitm                      # ...then open it

Or push the flows straight into a running mitmweb, replacing the ones it has:

    python test/helper_tools/gen_sample_flows.py --upload --token TOKEN

The token is the `?token=...` in the URL mitmweb prints on startup, or your `web_password`.
"""

from __future__ import annotations

import argparse
import http.cookiejar
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from mitmproxy import io
from mitmproxy.flow import Flow
from mitmproxy.http import Headers
from mitmproxy.test.tflow import tclient_conn
from mitmproxy.test.tflow import tdnsflow
from mitmproxy.test.tflow import terr
from mitmproxy.test.tflow import tflow
from mitmproxy.test.tflow import ttcpflow
from mitmproxy.test.tflow import tudpflow
from mitmproxy.test.tflow import twebsocket
from mitmproxy.test.tutils import treq
from mitmproxy.test.tutils import tresp

XSRF_COOKIE = "_mitmproxy_xsrf"


def _req(path: str, host: str = "example.com", tls: bool = True, **kwargs):
    return treq(
        host=host,
        port=443 if tls else 80,
        scheme=b"https" if tls else b"http",
        path=path.encode(),
        **kwargs,
    )


def _resp(status_code: int = 200, content_type: str | None = None, **headers):
    if content_type:
        headers["content_type"] = content_type
    headers.setdefault("content_length", "7")
    return tresp(status_code=status_code, headers=Headers(**headers))


def _plaintext_client():
    """A client connection that never completed a TLS handshake, so the TLS column stays grey."""
    conn = tclient_conn()
    conn.timestamp_tls_setup = None
    conn.tls = False
    return conn


def _quic_client():
    conn = tclient_conn()
    conn.tls_version = "QUICv1"
    conn.tls = True
    return conn


def resource_type_flows() -> list[tuple[str, Flow]]:
    """One flow per `ResourceType`, in the order the icons are worth comparing."""
    return [
        (
            "html",
            tflow(
                req=_req("/"),
                resp=_resp(content_type="text/html; charset=utf-8"),
            ),
        ),
        (
            "js",
            tflow(
                req=_req("/static/app.bundle.js"),
                resp=_resp(content_type="application/javascript"),
            ),
        ),
        (
            "css",
            tflow(
                req=_req("/static/main.css"),
                resp=_resp(content_type="text/css"),
            ),
        ),
        (
            "image",
            tflow(
                req=_req("/img/logo.png"),
                resp=_resp(content_type="image/png"),
            ),
        ),
        (
            "plain (unknown content type)",
            tflow(
                req=_req("/api/telemetry.bin"),
                resp=_resp(content_type="application/octet-stream"),
            ),
        ),
        (
            "plain (still in flight)",
            tflow(req=_req("/api/slow-endpoint"), live=True),
        ),
        (
            "not-modified",
            tflow(
                req=_req("/static/app.bundle.js"),
                resp=_resp(304, content_length="0"),
            ),
        ),
        (
            "redirect",
            tflow(
                client_conn=_plaintext_client(),
                req=_req("/old-path", tls=False),
                resp=_resp(301, location="https://example.com/new-path"),
            ),
        ),
        (
            "websocket",
            tflow(
                req=_req("/socket", method=b"GET"),
                resp=tresp(status_code=101, reason=b"Switching Protocols"),
                ws=twebsocket(),
            ),
        ),
        ("tcp", ttcpflow()),
        ("udp", tudpflow()),
        ("dns", tdnsflow(resp=True)),
        ("quic", tudpflow(client_conn=_quic_client())),
    ]


def flow_state_flows() -> list[tuple[str, Flow]]:
    """Row states that draw their own icons in the path and quickactions columns."""
    intercepted = tflow(req=_req("/checkout/submit", method=b"POST"))
    intercepted.intercepted = True

    killed = tflow(req=_req("/tracking/beacon"), err=terr("Connection killed."))

    errored = tflow(req=_req("/unreachable"), err=terr("Server unreachable"))

    replayed = tflow(req=_req("/api/session"), resp=_resp(content_type="text/html"))
    replayed.is_replay = "request"

    marked = tflow(req=_req("/interesting"), resp=_resp(content_type="text/html"))
    marked.marked = ":star:"
    marked.comment = "Worth a second look"

    return [
        ("intercepted", intercepted),
        ("killed", killed),
        ("error", errored),
        ("replayed", replayed),
        ("marked + comment", marked),
    ]


def stagger(flows: list[Flow], base: float) -> None:
    """Spread flows over the last few minutes so the time columns are not all identical."""
    for i, f in enumerate(flows):
        start = base + i * 3
        end = start + 0.05 * (i + 1)
        f.timestamp_created = start
        f.client_conn.timestamp_start = start
        if f.server_conn:
            f.server_conn.timestamp_start = start
            f.server_conn.timestamp_end = end
        match f.type:
            case "http":
                f.request.timestamp_start = start
                f.request.timestamp_end = start + 0.01
                if f.response:
                    f.response.timestamp_start = start + 0.02
                    f.response.timestamp_end = end
                if f.websocket:
                    f.websocket.timestamp_end = end
            case "tcp" | "udp":
                for j, msg in enumerate(f.messages):
                    msg.timestamp = start + 0.01 * (j + 1)
            case "dns":
                f.request.timestamp = start
                if f.response:
                    f.response.timestamp = end


def build() -> list[tuple[str, Flow]]:
    labelled = resource_type_flows() + flow_state_flows()
    stagger([f for _, f in labelled], time.time() - 300)
    return labelled


def upload(data: bytes, web_url: str, token: str) -> None:
    """POST the flows to a running mitmweb, mimicking what the UI's File > Open does."""
    jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))

    # Only the /updates handler mints an XSRF cookie (see IndexHandler's neighbours in tools/web/app.py),
    # and it does so in prepare() so the botched websocket handshake this provokes still leaves us with both the auth and XSRF cookies.
    try:
        opener.open(f"{web_url}/updates?token={token}").read()
    except urllib.error.HTTPError as e:
        if e.code != 400:
            raise
    try:
        xsrf = next(c.value for c in jar if c.name == XSRF_COOKIE)
    except StopIteration:
        sys.exit(
            f"mitmweb did not set a {XSRF_COOKIE} cookie; is {web_url} really mitmweb?"
        )

    request = urllib.request.Request(
        f"{web_url}/flows/dump",
        data=data,
        method="POST",
        headers={"X-XSRFToken": xsrf, "Content-Type": "application/octet-stream"},
    )
    opener.open(request).read()


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "-o",
        "--out",
        type=Path,
        default=Path("sample-flows.mitm"),
        help="output flow file",
    )
    parser.add_argument(
        "--upload",
        action="store_true",
        help="also load the flows into a running mitmweb",
    )
    parser.add_argument("--token", help="mitmweb auth token, required with --upload")
    parser.add_argument(
        "--web-url",
        default="http://127.0.0.1:8081",
        help="mitmweb address (not the proxy port)",
    )
    args = parser.parse_args()

    labelled = build()
    with args.out.open("wb") as fp:
        writer = io.FlowWriter(fp)
        for _, f in labelled:
            writer.add(f)

    for label, _ in labelled:
        print(f"  {label}")
    print(f"\n{len(labelled)} flows -> {args.out}")

    if not args.upload:
        print(f"\nOpen with:  mitmweb -r {args.out}")
        print("or in a running mitmweb via File > Open.")
        return

    if not args.token:
        sys.exit("--upload needs --token (the ?token=... mitmweb prints at startup)")
    try:
        upload(args.out.read_bytes(), args.web_url.rstrip("/"), args.token)
    except urllib.error.HTTPError as e:
        sys.exit(
            f"upload failed: {e.code} {e.reason} (a 403 usually means a stale token)"
        )
    except urllib.error.URLError as e:
        sys.exit(f"could not reach mitmweb at {args.web_url}: {e.reason}")
    print(f"\nUploaded to {args.web_url}, replacing the flows it had.")


if __name__ == "__main__":
    main()
