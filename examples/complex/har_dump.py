"""
This inline script can be used to dump flows as HAR files.

example cmdline invocation options:
Single file for entire session.
mitmdump -s ./har_dump.py --set harfile=./dump.har

One file per flow. Filenames will be the timestamp of the
request along with a 6 char hash of the URL. Files will have
.har for their extension.
mitmdump -s ./har_dump.py --set hardir=./hars

To set compression for files use the compress flag.
Options are "bzip2, gzip, zlib"
For one file per flow the extensions will be either
.har.bz2 (bzip2), .har.gz (gzip) or .zhar (zlib)
mitmdump -s ./har_dump.py --set harfile=./dump.har.gz --set compress=gzip
mitmdump -s ./har_dump.py --set hardir=./hars --set compress=zlib

OR

Single files with '.zhar' as the extension will be compressed using zlib
mitmdump -s ./har_dump.py --set harfile=./dump.zhar
"""


import base64
import bz2
import hashlib
import gzip
import json
import os
import typing  # noqa
import zlib

from datetime import datetime
from datetime import timezone

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
    l.add_option("harfile", str, "", "HAR dump file.")
    l.add_option("hardir", str, "", "HAR dump folder.")
    l.add_option("compress", str, "", "Compress files - bzip2, gzip or zlib")
    l.add_option("verbose", bool, False, "Verbose")


def configure(updated):
    if ctx.options.verbose:
        ctx.log("Option - harfile - %s" % ctx.options.harfile)
        ctx.log("Option - hardir - %s" % ctx.options.hardir)
        ctx.log("Option - compress - %s" % ctx.options.compress)

    prep_dict()


def prep_dict():
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

    if ctx.options.hardir:
        HAR["log"]["entries"] = [entry]
        filename = "%s-%s" % (flow.request.timestamp_start,
                              hashlib.sha1(flow.request.url.encode('utf-8')).hexdigest()[:6])

        if ctx.options.compress == "bzip2":
            filename = "%s.har.bz2" % filename
        elif ctx.options.compress == "gzip":
            filename = "%s.har.gz" % filename
        elif ctx.options.compress == "zlib":
            filename = "%s.zhar" % filename
        else:
            filename = "%s.har" % filename

        dump_file(os.path.join(ctx.options.hardir, filename))
        prep_dict()
    else:
        HAR["log"]["entries"].append(entry)


def done():
    """
        Called once on script shutdown, after any other events.
    """
    if ctx.options.harfile:
        dump_file(ctx.options.harfile)


def dump_file(filename):
    compress: str = ctx.options.compress
    json_dump: str = json.dumps(HAR, indent=2)

    if filename == '-':
        ctx.log(json_dump)
    else:
        raw: bytes = json_dump.encode()
        if compress == "bzip2":
            raw = bz2.compress(raw, 9)
        elif compress == "gzip":
            raw = gzip.compress(raw, 9)
        elif compress == "zlib":
            raw = zlib.compress(raw, 9)
        elif filename.endswith('.zhar'):
            raw = zlib.compress(raw, 9)

        with open(os.path.expanduser(filename), "wb") as f:
            f.write(raw)

        if ctx.options.verbose:
            if compress:
                ctx.log("HAR dump finished (wrote %s bytes (%s compressed) to %s)" % (len(json_dump), len(raw), filename))
            else:
                ctx.log("HAR dump finished (wrote %s bytes to file %s)" % (len(json_dump), filename))


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
