"""
This inline script can be used to dump flows as HAR files.
"""


import pprint
import json
import sys
import base64
import zlib

from datetime import datetime
import pytz

import mitmproxy

from netlib import version
from netlib import strutils
from netlib.http import cookies

HAR = {}

# A list of server seen till now is maintained so we can avoid
# using 'connect' time for entries that use an existing connection.
SERVERS_SEEN = set()


def start():
    """
        Called once on script startup before any other events.
    """
    if len(sys.argv) != 2:
        raise ValueError(
            'Usage: -s "har_dump.py filename" '
            '(- will output to stdout, filenames ending with .zhar '
            'will result in compressed har)'
        )

    HAR.update({
        "log": {
            "version": "1.2",
            "creator": {
                "name": "mitmproxy har_dump",
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

        if flow.server_conn.timestamp_ssl_setup is not None:
            ssl_time = (flow.server_conn.timestamp_ssl_setup -
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

    started_date_time = format_datetime(datetime.utcfromtimestamp(flow.request.timestamp_start))

    # Response body size and encoding
    response_body_size = len(flow.response.raw_content)
    response_body_decoded_size = len(flow.response.content)
    response_body_compression = response_body_decoded_size - response_body_size

    entry = {
        "startedDateTime": started_date_time,
        "time": full_time,
        "request": {
            "method": flow.request.method,
            "url": flow.request.url,
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

    # Store binay data as base64
    if strutils.is_mostly_bin(flow.response.content):
        b64 = base64.b64encode(flow.response.content)
        entry["response"]["content"]["text"] = b64.decode('ascii')
        entry["response"]["content"]["encoding"] = "base64"
    else:
        entry["response"]["content"]["text"] = flow.response.text

    if flow.request.method in ["POST", "PUT", "PATCH"]:
        entry["request"]["postData"] = {
            "mimeType": flow.request.headers.get("Content-Type", "").split(";")[0],
            "text": flow.request.content,
            "params": name_value(flow.request.urlencoded_form)
        }

    if flow.server_conn:
        entry["serverIPAddress"] = str(flow.server_conn.ip_address.address[0])

    HAR["log"]["entries"].append(entry)


def done():
    """
        Called once on script shutdown, after any other events.
    """
    dump_file = sys.argv[1]

    if dump_file == '-':
        mitmproxy.ctx.log(pprint.pformat(HAR))
    else:
        json_dump = json.dumps(HAR, indent=2)

        if dump_file.endswith('.zhar'):
            json_dump = zlib.compress(json_dump, 9)

        with open(dump_file, "w") as f:
            f.write(json_dump)

        mitmproxy.ctx.log("HAR dump finished (wrote %s bytes to file)" % len(json_dump))


def format_datetime(dt):
    return dt.replace(tzinfo=pytz.timezone("UTC")).isoformat()


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
            cookie_har["expires"] = format_datetime(datetime.fromtimestamp(expire_ts))

        rv.append(cookie_har)

    return rv


def format_request_cookies(fields):
    return format_cookies(cookies.group_cookies(fields))


def format_response_cookies(fields):
    return format_cookies((c[0], c[1].value, c[1].attrs) for c in fields)


def name_value(obj):
    """
        Convert (key, value) pairs to HAR format.
    """
    return [{"name": k, "value": v} for k, v in obj.items()]
