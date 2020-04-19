import re
import json

import typing

from mitmproxy.contentviews import base

PARSE_ERROR = object()


def parse_json(s: bytes) -> typing.Any:
    try:
        return json.loads(s.decode('utf-8'))
    except ValueError:
        return PARSE_ERROR


def format_json(data: typing.Any) -> typing.Iterator[base.TViewLine]:
    encoder = json.JSONEncoder(indent=4, sort_keys=True, ensure_ascii=False)
    current_line: base.TViewLine = []
    for chunk in encoder.iterencode(data):
        if "\n" in chunk:
            rest_of_last_line, chunk = chunk.split("\n", maxsplit=1)
            # rest_of_last_line is a delimiter such as , or [
            current_line.append(('text', rest_of_last_line))
            yield current_line
            current_line = []
        if re.match(r'\s*"', chunk):
            current_line.append(('json_string', chunk))
        elif re.match(r'\s*\d', chunk):
            current_line.append(('json_number', chunk))
        elif re.match(r'\s*(true|null|false)', chunk):
            current_line.append(('json_boolean', chunk))
        else:
            current_line.append(('text', chunk))
    yield current_line


class ViewJSON(base.View):
    name = "JSON"
    content_types = [
        "application/json",
        "application/json-rpc",
        "application/vnd.api+json"
    ]

    def __call__(self, data, **metadata):
        data = parse_json(data)
        if data is not PARSE_ERROR:
            return "JSON", format_json(data)
