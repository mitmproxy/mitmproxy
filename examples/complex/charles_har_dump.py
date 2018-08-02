"""
This inline script can be used to dump flows as HAR files in a format that Charles will display correctly.
Shamelessly copied from the work at https://github.com/mitmproxy/mitmproxy/blob/master/examples/complex/har_dump.py with tiny modifications.

example cmdline invocation:
mitmdump -s ./charles_har_dump.py --set hardump=./dump.har

filename endwith '.zhar' will be compressed:
mitmdump -s ./charles_har_dump.py --set hardump=./dump.zhar
"""


import json
import base64
import zlib
import os
import typing  # noqa

from datetime import datetime
from datetime import timezone

import mitmproxy

from mitmproxy import connections  # noqa
from mitmproxy import version
from mitmproxy import ctx
from mitmproxy.utils import strutils
from mitmproxy.net.http import cookies

HAR: typing.Dict = {}

# A list of server seen till now is maintained so we can avoid
# using 'connect' time for entries that use an existing connection.
SERVERS_SEEN: typing.Set[connections.ServerConnection] = set()


def load(l):
    l.add_option(
        "hardump", str, "", "HAR dump path.",
    )


def configure(updated):
    HAR.update({
        "log": {
            "version": "1.2",
            "creator": {
                "name": "mitmproxy charles_har_dump",
                "version": "0.1",
                "comment": "mitmproxy version %s" % version.MITMPROXY
            },
            "entries": []
        }
    })


def response(flow):
    """
       Called when a server response has been received.
    """

    # -1 indicates that these values do not apply to current request
    ssl_time = -1
    connect_time = -1

    if flow.server_conn and flow.server_conn not in SERVERS_SEEN:
        connect_time = (flow.server_conn.timestamp_tcp_setup -
                        flow.server_conn.timestamp_start)

        if flow.server_conn.timestamp_tls_setup is not None:
            ssl_time = (flow.server_conn.timestamp_tls_setup -
                        flow.server_conn.timestamp_tcp_setup)

        SERVERS_SEEN.add(flow.server_conn)

    # Calculate raw timings from timestamps. DNS timings can not be calculated
    # for lack of a way to measure it. The same goes for HAR blocked.
    # mitmproxy will open a server connection as soon as it receives the host
    # and port from the client connection. So, the time spent waiting is actually
    # spent waiting between request.timestamp_end and response.timestamp_start
    # thus it correlates to HAR wait instead.
    timings_raw = {
        'send': flow.request.timestamp_end - flow.request.timestamp_start,
        'receive': flow.response.timestamp_end - flow.response.timestamp_start,
        'wait': flow.response.timestamp_start - flow.request.timestamp_end,
        'connect': connect_time,
        'ssl': ssl_time,
    }

    # HAR timings are integers in ms, so we re-encode the raw timings to that format.
    timings = dict([(k, int(1000 * v)) for k, v in timings_raw.items()])

    # full_time is the sum of all timings.
    # Timings set to -1 will be ignored as per spec.
    full_time = sum(v for v in timings.values() if v > -1)

    started_date_time = datetime.fromtimestamp(flow.request.timestamp_start, timezone.utc).isoformat()

    # Response body size and encoding
    response_body_size = len(flow.response.raw_content)
    response_body_decoded_size = len(flow.response.content)
    response_body_compression = response_body_decoded_size - response_body_size

    # Changing request.url to display the DNS name.
    # Charles Proxy can't display the response host as the host
    # so we have to trick it in the conversion.
    # No Host header? IP gets used instead like the har_dump.py behavior
    entry = {
        "startedDateTime": started_date_time,
        "time": full_time,
        "request": {
            "method": flow.request.method,
            "url": extract_header_host_name(flow),
            "httpVersion": flow.request.http_version,
            "cookies": format_request_cookies(flow.request.cookies.fields),
            "headers": name_value(flow.request.headers),
            "queryString": name_value(flow.request.query or {}),
            "headersSize": len(str(flow.request.headers)),
            "bodySize": len(flow.request.content),
        },
        "response": {
            "status": flow.response.status_code,
            "statusText": flow.response.reason,
            "httpVersion": flow.response.http_version,
            "cookies": format_response_cookies(flow.response.cookies.fields),
            "headers": name_value(flow.response.headers),
            "content": {
                "size": response_body_size,
                "compression": response_body_compression,
                "mimeType": flow.response.headers.get('Content-Type', '')
            },
            "redirectURL": flow.response.headers.get('Location', ''),
            "headersSize": len(str(flow.response.headers)),
            "bodySize": response_body_size,
        },
        "cache": {},
        "timings": timings,
    }

    # Store binary data as base64
    if strutils.is_mostly_bin(flow.response.content):
        entry["response"]["content"]["text"] = base64.b64encode(flow.response.content).decode()
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
            "params": params
        }

    if flow.server_conn.connected():
        entry["serverIPAddress"] = str(flow.server_conn.ip_address[0])

    HAR["log"]["entries"].append(entry)


def done():
    """
        Called once on script shutdown, after any other events.
    """
    if ctx.options.hardump:
        json_dump: str = json.dumps(HAR, indent=2)

        if ctx.options.hardump == '-':
            mitmproxy.ctx.log(json_dump)
        else:
            raw: bytes = json_dump.encode()
            if ctx.options.hardump.endswith('.zhar'):
                raw = zlib.compress(raw, 9)

            with open(os.path.expanduser(ctx.options.hardump), "wb") as f:
                f.write(raw)

            mitmproxy.ctx.log("HAR dump finished (wrote %s bytes to file)" % len(json_dump))


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
            cookie_har["expires"] = datetime.fromtimestamp(expire_ts, timezone.utc).isoformat()

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


def extract_header_host_name(obj):
    """
        Grab just the header Host value to sub in for URLs for other clients
        Copies same sort of logic as name_value, but extracts just the value.
        Also, if there's not a Host header, we just go back to the flow.request.url
    """
    header_object = obj.request.headers
    host_name = "none"
    for name, value in header_object.items():
        if name == "Host":
            host_name = value
    if host_name == "none":
        return obj.request.url
    else:
        return host_name