import base64
import json
import logging
from datetime import datetime
from datetime import timezone

from mitmproxy import command
from mitmproxy import version
from mitmproxy.utils import strutils
from mitmproxy import flow
from mitmproxy import http
from mitmproxy import types
from collections.abc import Iterable


logger = logging.getLogger(__name__)


class ExportHar:
    def __init__(self):
        # used to store unique server connections
        self.servers_seen = set()

    def format_request_cookies(self, request: http.Request) -> list[dict[str, str]]:
        cookie_list = request.cookies.items(multi=True)

        rv = []

        for key, value in cookie_list:
            rv.append({"name": key, "value": value})
        return rv

    def format_response_cookies(self, response: http.Response) -> list[dict]:
        cookie_list = response.cookies.items(multi=True)
        rv = []
        for name, (value, attrs) in cookie_list:
            cookie = {
                "name": name,
                "value": value,
                "path": attrs["path"],
                "domain": attrs["domain"],
                "expires": attrs["expires"],
                "httpOnly": "httpOnly" in attrs,
                "secure": "secure" in attrs,
            }
            if attrs.get("expires") != None:
                # date is given as 'Wed, 24-Jul-2024 12:58:46 GMT' format but need to be '2024-07-24T12:58:46.000Z' format
                output_date_string = datetime.strptime(
                    attrs["expires"], "%a, %d-%b-%Y %H:%M:%S %Z"
                ).strftime("%Y-%m-%dT%H:%M:%S.000Z")
                cookie["expires"] = output_date_string

            if "sameSite" in attrs:
                cookie["sameSite"] = attrs["sameSite"]

            rv.append(cookie)
        return rv

    def name_value(self, obj: http.Headers) -> list[dict]:
        return [{"name": k, "value": v} for k, v in obj.items()]

    def flow_entry(self, flow: flow.Flow) -> dict:
        ssl_time = -1
        connect_time = -1

        if flow.server_conn not in self.servers_seen:
            connect_time = (flow.server_conn.timestamp_tcp_setup or 0) - (
                flow.server_conn.timestamp_start or 0
            )
            if (
                flow.server_conn.timestamp_tls_setup
                and flow.server_conn.timestamp_tcp_setup
            ):
                ssl_time = (
                    flow.server_conn.timestamp_tls_setup
                    - flow.server_conn.timestamp_tcp_setup
                )
            self.servers_seen.add(flow.server_conn)

        if flow.response:
            timings_raw = {
                "send": flow.request.timestamp_end - flow.request.timestamp_start,
                "receive": flow.response.timestamp_end - flow.response.timestamp_start,
                "wait": flow.response.timestamp_start - flow.request.timestamp_end,
                "connect": connect_time,
                "ssl": ssl_time,
            }
        elif flow.error:
            timings_raw = {
                "send": 0,
                "receive": 0,
                "wait": 0,
                "connect": -1,
                "ssl": -1,
                "blocked": flow.request.timestamp_end - flow.request.timestamp_start,
            }
        else:
            timings_raw = {
                "send": flow.request.timestamp_end - flow.request.timestamp_start,
                "receive": 0,
                "wait": 0,
                "connect": connect_time,
                "ssl": ssl_time,
            }

        timings = {k: int(1000 * v) if v != -1 else -1 for k, v in timings_raw.items()}
        full_time = sum(v for v in timings.values() if v > -1)
        started_date_time = datetime.fromtimestamp(
            flow.request.timestamp_start, timezone.utc
        ).isoformat()

        if not flow.response:
            response = {
                "status": 0,
                "statusText": "",
                "httpVersion": "",
                "headers": [],
                "cookies": [],
                "redirectURL": "",
                "headersSize": -1,
                "bodySize": -1,
                "_transferSize": 0,
                "_error": None,
            }
            if flow.error:
                response["_error"] = flow.error.msg
        else:
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
                "headers": self.name_value(flow.response.headers),
                "content": {
                    "size": response_body_size,
                    "compression": response_body_compression,
                    "mimeType": flow.response.headers.get("Content-Type", ""),
                },
                "redirectURL": flow.response.headers.get("Location", ""),
                "headersSize": len(str(flow.response.headers)),
                "bodySize": response_body_size,
            }

        entry = {
            "startedDateTime": started_date_time,
            "time": full_time,
            "request": {
                "method": flow.request.method,
                "url": flow.request.pretty_url,
                "httpVersion": flow.request.http_version,
                "cookies": self.format_request_cookies(flow.request),
                "headers": self.name_value(flow.request.headers),
                "queryString": self.name_value(flow.request.query),
                "headersSize": len(str(flow.request.headers)),
                "bodySize": len(flow.request.content),
            },
            "response": response,
            "cache": {},
            "timings": timings,
        }

        if not flow.response:
            entry["response"]["content"] = []
        elif strutils.is_mostly_bin(flow.response.content):
            entry["response"]["content"] = {
                "text": base64.b64encode(flow.response.content).decode(),
                "encoding": "base64",
            }
        else:
            entry["response"]["content"] = {
                "text": flow.response.get_text(strict=False)
            }

        if flow.request.method in ["POST", "PUT", "PATCH"]:
            params = [
                {"name": a, "value": b}
                for a, b in flow.request.urlencoded_form.items(multi=True)
            ]
            entry["request"]["postData"] = {
                "mimeType": flow.request.headers.get("Content-Type", ""),
                "text": flow.request.get_text(strict=False),
                "params": params,
            }

        if flow.server_conn.connected:
            entry["serverIPAddress"] = str(flow.server_conn.peername[0])

        return entry

    @command.command("exporthar")
    def export_har(self, flows: Iterable[flow.Flow], path: types.Path) -> None:
        har = {
            "log": {
                "version": "1.2",
                "creator": {
                    "name": "mitmproxy exporthar",
                    "version": "0.1",
                    "comment": "mitmproxy version %s" % version.MITMPROXY,
                },
                "pages": [],
                "entries": [self.flow_entry(flow) for flow in flows],
            }
        }
        with open(path, "w") as fp:
            json.dump(har, fp, indent=4)


addons = [ExportHar()]
