"""Write flow objects to a HAR file"""
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
from mitmproxy import version
from mitmproxy.connection import Server
from mitmproxy.coretypes.multidict import _MultiDict
from mitmproxy.exceptions import CommandError
from mitmproxy.utils import strutils

logger = logging.getLogger(__name__)


class ExportHar:
    @command.command("exporthar")
    def export_har(self, flows: Sequence[flow.Flow], path: types.Path) -> None:
        """Export flows to an HAR (HTTP Archive) file."""
        entries = []

        # A list of server seen till now is maintained so we can avoid
        # using 'connect' time for entries that use an existing connection.
        servers_seen: set[Server] = set()

        for f in flows:
            if isinstance(f, http.HTTPFlow):
                entries.append(self.flow_entry(f, servers_seen))
            else:
                raise CommandError(f"Cannot export {type(f).__name__} flows to HAR.")

        har = {
            "log": {
                "version": "1.2",
                "creator": {
                    "name": "mitmproxy exporthar",
                    "version": "0.1",
                    "comment": f"mitmproxy version {version.MITMPROXY}",
                },
                "pages": [],
                "entries": entries,
            }
        }
        with open(path, "w") as fp:
            json.dump(har, fp, indent=4)

    def flow_entry(self, flow: http.HTTPFlow, servers_seen: set[Server]) -> dict:
        """Creates HAR entry from flow"""

        if flow.server_conn in servers_seen:
            connect_time = -1.0
            ssl_time = -1.0
        elif flow.server_conn.timestamp_tcp_setup:
            assert flow.server_conn.timestamp_start
            connect_time = 1000 * (
                flow.server_conn.timestamp_tcp_setup - flow.server_conn.timestamp_start
            )

            if flow.server_conn.timestamp_tls_setup:
                ssl_time = 1000 * (
                    flow.server_conn.timestamp_tls_setup
                    - flow.server_conn.timestamp_tcp_setup
                )
            else:
                ssl_time = None
            servers_seen.add(flow.server_conn)
        else:
            connect_time = None
            ssl_time = None

        if flow.request.timestamp_end:
            send = 1000 * (flow.request.timestamp_end - flow.request.timestamp_start)
        else:
            send = 0

        if flow.response and flow.request.timestamp_end:
            wait = 1000 * (flow.response.timestamp_start - flow.request.timestamp_end)
        else:
            wait = 0

        if flow.response and flow.response.timestamp_end:
            receive = 1000 * (
                flow.response.timestamp_end - flow.response.timestamp_start
            )
        else:
            receive = 0

        timings: dict[str, float | None] = {
            "connect": connect_time,
            "ssl": ssl_time,
            "send": send,
            "receive": receive,
            "wait": wait,
        }

        if flow.response:
            response_body_size = (
                len(flow.response.raw_content) if flow.response.raw_content else 0
            )
            response_body_decoded_size = (
                len(flow.response.content) if flow.response.content else 0
            )
            response_body_compression = response_body_decoded_size - response_body_size
            response = {
                "status": flow.response.status_code,
                "statusText": flow.response.reason,
                "httpVersion": flow.response.http_version,
                "cookies": self.format_response_cookies(flow.response),
                "headers": self.format_multidict(flow.response.headers),
                "content": {
                    "size": response_body_size,
                    "compression": response_body_compression,
                    "mimeType": flow.response.headers.get("Content-Type", ""),
                },
                "redirectURL": flow.response.headers.get("Location", ""),
                "headersSize": len(str(flow.response.headers)),
                "bodySize": response_body_size,
            }
            if flow.response.content and strutils.is_mostly_bin(flow.response.content):
                response["content"]["text"] = base64.b64encode(
                    flow.response.content
                ).decode()
                response["content"]["encoding"] = "base64"
            else:
                response["content"]["text"] = flow.response.get_text(strict=False)
        else:
            response = {
                "status": 0,
                "statusText": "",
                "httpVersion": "",
                "headers": [],
                "cookies": [],
                "content": {},
                "redirectURL": "",
                "headersSize": -1,
                "bodySize": -1,
                "_transferSize": 0,
                "_error": None,
            }
            if flow.error:
                response["_error"] = flow.error.msg

        entry: dict[str, Any] = {
            "startedDateTime": datetime.fromtimestamp(
                flow.request.timestamp_start, timezone.utc
            ).isoformat(),
            "time": sum(v for v in timings.values() if v is not None and v >= 0),
            "request": {
                "method": flow.request.method,
                "url": flow.request.pretty_url,
                "httpVersion": flow.request.http_version,
                "cookies": self.format_multidict(flow.request.cookies),
                "headers": self.format_multidict(flow.request.headers),
                "queryString": self.format_multidict(flow.request.query),
                "headersSize": len(str(flow.request.headers)),
                "bodySize": len(flow.request.content) if flow.request.content else 0,
            },
            "response": response,
            "cache": {},
            "timings": timings,
        }

        if flow.request.method in ["POST", "PUT", "PATCH"]:
            params = self.format_multidict(flow.request.urlencoded_form)
            entry["request"]["postData"] = {
                "mimeType": flow.request.headers.get("Content-Type", ""),
                "text": flow.request.get_text(strict=False),
                "params": params,
            }

        if flow.server_conn.peername:
            entry["serverIPAddress"] = str(flow.server_conn.peername[0])

        return entry

    def format_response_cookies(self, response: http.Response) -> list[dict]:
        """Formats the response's cookie header to list of cookies"""
        cookie_list = response.cookies.items(multi=True)
        rv = []
        for name, (value, attrs) in cookie_list:
            cookie = {
                "name": name,
                "value": value,
                "path": attrs["path"],
                "domain": attrs["domain"],
                "httpOnly": "httpOnly" in attrs,
                "secure": "secure" in attrs,
            }
            # TODO: handle expires attribute here.
            # This is not quite trivial because we need to parse random date formats.
            # For now, we just ignore the attribute.

            if "sameSite" in attrs:
                cookie["sameSite"] = attrs["sameSite"]

            rv.append(cookie)
        return rv

    def format_multidict(self, obj: _MultiDict[str, str]) -> list[dict]:
        return [{"name": k, "value": v} for k, v in obj.items(multi=True)]


addons = [ExportHar()]
