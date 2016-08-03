"""
This inline script can be used to dump flows as HAR files.
"""


import pprint
import json
import sys

from datetime import datetime
import pytz

import mitmproxy
from mitmproxy import version

HAR = {}


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
    entries = HAR["log"]["entries"]

    # TODO: SSL and Connect Timings

    # Calculate raw timings from timestamps.

    # DNS timings can not be calculated for lack of a way to measure it.
    # The same goes for HAR blocked.

    # mitmproxy will open a server connection as soon as it receives the host
    # and port from the client connection. So, the time spent waiting is actually
    # spent waiting between request.timestamp_end and response.timestamp_start thus it
    # correlates to HAR wait instead.
    timings_raw = {
        'send': flow.request.timestamp_end - flow.request.timestamp_start,
        'receive': flow.response.timestamp_end - flow.response.timestamp_start,
        'wait': flow.response.timestamp_start - flow.request.timestamp_end,
    }

    # HAR timings are integers in ms, so we re-encode the raw timings to that format.
    timings = dict([(k, int(1000 * v)) for k, v in timings_raw.items()])

    # full_time is the sum of all timings.
    # Timings set to -1 will be ignored as per spec.
    full_time = sum(v for v in timings.values() if v > -1)

    started_date_time = datetime.utcfromtimestamp(
        flow.request.timestamp_start).replace(tzinfo=pytz.timezone("UTC")).isoformat()

    # Size calculations
    response_body_size = len(flow.response.content)
    response_body_decoded_size = len(flow.response.content)
    response_body_compression = response_body_decoded_size - response_body_size

    entries.append({
        "startedDateTime": started_date_time,
        "time": full_time,
        "request": {
            "method": flow.request.method,
            "url": flow.request.url,
            "httpVersion": flow.request.http_version,
            "cookies": name_value(flow.request.cookies),
            "headers": name_value(flow.request.headers),
            "queryString": name_value(flow.request.query or {}),
            "headersSize": len(str(flow.request.headers)),
            "bodySize": len(flow.request.content),
        },
        "response": {
            "status": flow.response.status_code,
            "statusText": flow.response.reason,
            "httpVersion": flow.response.http_version,
            "cookies": name_value(flow.response.cookies),
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
    })


def done():
    """
        Called once on script shutdown, after any other events.
    """
    dump_file = sys.argv[1]

    if dump_file == '-':
        mitmproxy.ctx.log(pprint.pformat(HAR))
    # TODO: .zhar compression
    else:
        with open(dump_file, "wb") as f:
            f.write(json.dumps(HAR, indent=2))

    # TODO: Log results via mitmproxy.ctx.log


def name_value(obj):
    """
        Convert (key, value) pairs to HAR format.
    """

    items = []
    if hasattr(obj, 'fields'):
        items = obj.fields
    elif hasattr(obj, 'items'):
        items = obj.items()

    if items:
        return [{"name": k, "value": v} for k, v in items]
    else:
        return ""
