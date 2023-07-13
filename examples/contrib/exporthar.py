"""Exports flow objects into HAR files"""
import base64
import json
import logging
from collections.abc import Sequence
from datetime import datetime
from datetime import timezone

from mitmproxy import command
from mitmproxy import connection
from mitmproxy import flow
from mitmproxy import http
from mitmproxy import types
from mitmproxy import version
from mitmproxy.net.http import cookies
from mitmproxy.utils import strutils

logger = logging.getLogger(__name__)

ERROR_RESPONSE = {
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


def format_cookies(cookie_list):
    rv = []

    for name, value, attrs in cookie_list:
        cookie_har = {
            "name": name,
            "value": value,
        }

        # HAR only needs some attributes
        for key in ["path", "domain", "comment"]:
            if key in attrs:
                cookie_har[key] = attrs[key]

        # These keys need to be boolean!
        for key in ["httpOnly", "secure"]:
            cookie_har[key] = bool(key in attrs)

        # Expiration time needs to be formatted
        expire_ts = cookies.get_expiration_ts(attrs)
        if expire_ts is not None:
            cookie_har["expires"] = datetime.fromtimestamp(
                expire_ts, timezone.utc
            ).isoformat()

        rv.append(cookie_har)

    return rv


def format_request_cookies(fields):
    return format_cookies(cookies.group_cookies(fields))


def format_response_cookies(fields):
    return format_cookies((c[0], c[1][0], c[1][1]) for c in fields)


def name_value(obj):
    """
    Convert (key, value) pairs to HAR format.
    """
    return [{"name": k, "value": v} for k, v in obj.items()]


class ExportHar:
    def __init__(self) -> None:
        self.SERVERS_SEEN: set[connection.Server] = set()

    def flow_entry(self, flow: http.HTTPFlow) -> dict:
        # -1 indicates that these values do not apply to current request
        ssl_time = -1
        connect_time = -1

        if flow.server_conn not in self.SERVERS_SEEN:
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

            self.SERVERS_SEEN.add(flow.server_conn)

        # Calculate raw timings from timestamps. DNS timings can not be calculated
        # for lack of a way to measure it. The same goes for HAR blocked.
        # mitmproxy will open a server connection as soon as it receives the host
        # and port from the client connection. So, the time spent waiting is actually
        # spent waiting between request.timestamp_end and response.timestamp_start
        # thus it correlates to HAR wait instead.

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
        # HAR timings are integers in ms, so we re-encode the raw timings to that format.
        timings = {k: int(1000 * v) if v != -1 else -1 for k, v in timings_raw.items()}

        # full_time is the sum of all timings.
        # Timings set to -1 will be ignored as per spec.
        full_time = sum(v for v in timings.values() if v > -1)

        started_date_time = datetime.fromtimestamp(
            flow.request.timestamp_start, timezone.utc
        ).isoformat()

        # Response body size and encoding
        if not flow.response:
            response = ERROR_RESPONSE.copy()

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
                "cookies": format_response_cookies(flow.response.cookies.fields),
                "headers": name_value(flow.response.headers),
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
                "cookies": format_request_cookies(flow.request.cookies.fields),
                "headers": name_value(flow.request.headers),
                "queryString": name_value(flow.request.query),
                "headersSize": len(str(flow.request.headers)),
                "bodySize": len(flow.request.content),
            },
            "response": response,
            "cache": {},
            "timings": timings,
        }

        # Store binary data as base64
        if not flow.response:
            entry["response"]["content"] = []
        elif strutils.is_mostly_bin(flow.response.content):
            entry["response"]["content"]["text"] = base64.b64encode(
                flow.response.content
            ).decode()
            entry["response"]["content"]["encoding"] = "base64"
        else:
            entry["response"]["content"]["text"] = flow.response.get_text(strict=False)

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
    def export_har(self, flows: Sequence[flow.Flow], path: types.Path) -> None:
        """Writes given flows into HAR files"""
        HAR = {
            "log": {
                "version": "1.2",
                "creator": {
                    "name": "mitmproxy exporthar",
                    "version": "0.1",
                    "comment": "mitmproxy version %s" % version.MITMPROXY,
                },
                "pages": [],
                "entries": [],
            }
        }
        for flow in flows:
            HAR["log"]["entries"].append(self.flow_entry(flow))
        with open(path, "w") as fp:
            json.dump(HAR, fp, indent=4)


addons = [ExportHar()]
