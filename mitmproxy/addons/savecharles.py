"""Write flow objects to a Charles Proxy JSON Session (.chlsj) file."""

from __future__ import annotations

import base64
import json
import logging
from collections.abc import Sequence
from datetime import datetime
from datetime import timezone
from typing import Any

from mitmproxy import command
from mitmproxy import flow
from mitmproxy import http
from mitmproxy import types
from mitmproxy.log import ALERT
from mitmproxy.utils import human
from mitmproxy.utils import strutils

logger = logging.getLogger(__name__)


def _isofmt(ts: float | None) -> str | None:
    if ts is None:
        return None
    return datetime.fromtimestamp(ts, timezone.utc).isoformat()


def _ms(delta: float | None) -> int:
    if delta is None or delta < 0:
        return 0
    return int(round(delta * 1000))


def _split_content_type(value: str) -> tuple[str | None, str | None]:
    if not value:
        return None, None
    parts = [p.strip() for p in value.split(";")]
    mime = parts[0] or None
    charset: str | None = None
    for part in parts[1:]:
        if part.lower().startswith("charset="):
            charset = part.split("=", 1)[1].strip().strip('"') or None
    return mime, charset


def _body(message: http.Message | None) -> dict[str, Any]:
    if message is None or not message.raw_content:
        return {}
    raw = message.raw_content
    text = message.get_text(strict=False)
    if text is None or strutils.is_mostly_bin(raw):
        return {
            "encoded": base64.b64encode(raw).decode(),
            "charSet": "",
        }
    return {"text": text}


def _http_version_string(http_version: str) -> str:
    if not http_version:
        return "HTTP/1.1"
    if http_version.upper().startswith("HTTP/"):
        return http_version
    return f"HTTP/{http_version}"


def _headers_list(message: http.Message) -> list[dict[str, str]]:
    return [{"name": k, "value": v} for k, v in message.headers.items(multi=True)]


class SaveCharles:
    @command.command("save.charles")
    def export_charles(
        self, flows: Sequence[flow.Flow], path: types.Path
    ) -> None:
        """Export flows to a Charles Proxy JSON Session (.chlsj) file."""
        data = json.dumps(self.make_charles(flows), indent=4).encode()
        with open(path, "wb") as f:
            f.write(data)
        logging.log(
            ALERT,
            f"Charles JSON session saved ({human.pretty_size(len(data))} bytes).",
        )

    def make_charles(self, flows: Sequence[flow.Flow]) -> list[dict[str, Any]]:
        entries: list[dict[str, Any]] = []
        skipped = 0
        for f in flows:
            if isinstance(f, http.HTTPFlow):
                entries.append(self.flow_entry(f))
            else:
                skipped += 1
        if skipped:
            logger.info(f"Skipped {skipped} flows that weren't HTTP flows.")
        return entries

    def flow_entry(self, f: http.HTTPFlow) -> dict[str, Any]:
        req = f.request
        resp = f.response

        if f.error:
            status = "Failed"
        elif resp:
            status = "Complete"
        else:
            status = "Active"

        # Path/query split
        if "?" in req.path:
            path, _, query = req.path.partition("?")
        else:
            path, query = req.path, ""

        # Times
        times: dict[str, str | None] = {
            "start": _isofmt(req.timestamp_start),
        }
        if req.timestamp_end is not None:
            times["request"] = _isofmt(req.timestamp_end)
        if resp is not None:
            times["response"] = _isofmt(resp.timestamp_start)
        if resp is not None and resp.timestamp_end is not None:
            times["end"] = _isofmt(resp.timestamp_end)
        elif req.timestamp_end is not None:
            times["end"] = _isofmt(req.timestamp_end)
        else:
            times["end"] = times["start"]

        # Timing (in ms)
        sc = f.server_conn
        if sc and sc.timestamp_start and sc.timestamp_tcp_setup:
            connect_ms = _ms(sc.timestamp_tcp_setup - sc.timestamp_start)
        else:
            connect_ms = 0
        if sc and sc.timestamp_tcp_setup and sc.timestamp_tls_setup:
            ssl_ms = _ms(sc.timestamp_tls_setup - sc.timestamp_tcp_setup)
        else:
            ssl_ms = 0
        if req.timestamp_end is not None:
            request_ms = _ms(req.timestamp_end - req.timestamp_start)
        else:
            request_ms = 0
        if resp is not None and resp.timestamp_end is not None:
            response_ms = _ms(resp.timestamp_end - resp.timestamp_start)
        else:
            response_ms = 0
        if resp is not None and req.timestamp_end is not None:
            latency_ms = _ms(resp.timestamp_start - req.timestamp_end)
        else:
            latency_ms = 0
        end_ts = (
            (resp.timestamp_end if resp and resp.timestamp_end is not None else None)
            or (resp.timestamp_start if resp else None)
            or req.timestamp_end
            or req.timestamp_start
        )
        duration_ms = _ms(end_ts - req.timestamp_start) if end_ts else 0

        timing = {
            "dnsNs": 0,
            "connectMs": connect_ms,
            "sslMs": ssl_ms,
            "requestMs": request_ms,
            "responseMs": response_ms,
            "latencyMs": latency_ms,
            "durationMs": duration_ms,
            "totalMs": duration_ms,
        }

        # Connection addresses
        remote_address = ""
        if sc and sc.peername:
            remote_address = str(sc.peername[0])
        client_address = ""
        client_port = 0
        if f.client_conn and f.client_conn.peername:
            client_address = str(f.client_conn.peername[0])
            client_port = int(f.client_conn.peername[1])

        # Request side
        req_mime, req_charset = _split_content_type(
            req.headers.get("Content-Type", "")
        )
        req_encoding = req.headers.get("Content-Encoding") or None
        request_obj: dict[str, Any] = {
            "sizes": {
                "headers": len(str(req.headers)),
                "body": len(req.raw_content) if req.raw_content else 0,
            },
            "mimeType": req_mime,
            "charset": req_charset,
            "contentEncoding": req_encoding,
            "header": {
                "firstLine": f"{req.method} {req.path} {_http_version_string(req.http_version)}",
                "headers": _headers_list(req),
            },
            "body": _body(req),
        }

        # Response side
        if resp is not None:
            resp_mime, resp_charset = _split_content_type(
                resp.headers.get("Content-Type", "")
            )
            resp_encoding = resp.headers.get("Content-Encoding") or None
            response_obj: dict[str, Any] | None = {
                "status": resp.status_code,
                "sizes": {
                    "headers": len(str(resp.headers)),
                    "body": len(resp.raw_content) if resp.raw_content else 0,
                },
                "mimeType": resp_mime,
                "charset": resp_charset,
                "contentEncoding": resp_encoding,
                "header": {
                    "firstLine": f"{_http_version_string(resp.http_version)} {resp.status_code} {resp.reason}",
                    "headers": _headers_list(resp),
                },
                "body": _body(resp),
            }
        else:
            response_obj = None

        entry: dict[str, Any] = {
            "status": status,
            "method": req.method,
            "protocolVersion": _http_version_string(req.http_version),
            "scheme": req.scheme,
            "host": req.pretty_host,
            "actualPort": req.port,
            "path": path,
            "query": query,
            "remoteAddress": remote_address,
            "clientAddress": client_address,
            "clientPort": client_port,
            "times": times,
            "timing": timing,
            "tunnel": req.method == "CONNECT",
            "keptAlive": False,
            "webSocketMessages": [],
            "request": request_obj,
            "response": response_obj,
        }

        if f.error:
            entry["failure"] = f.error.msg

        if f.websocket is not None:
            ws_messages = []
            for m in f.websocket.messages:
                if m.is_text:
                    data = m.text
                    binary = False
                else:
                    data = base64.b64encode(m.content).decode()
                    binary = True
                ws_messages.append(
                    {
                        "type": "Send" if m.from_client else "Receive",
                        "time": _isofmt(m.timestamp),
                        "opcode": m.type.value,
                        "data": data,
                        "binary": binary,
                    }
                )
            entry["webSocketMessages"] = ws_messages

        return entry
