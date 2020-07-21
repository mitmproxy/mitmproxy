import pprint
import re
import typing

import msgpack


from mitmproxy.contentviews import base

PARSE_ERROR = object()


def parse_msgpack(s: bytes) -> typing.Any:
    try:
        return msgpack.unpackb(s, raw=False)
    except (ValueError, msgpack.ExtraData, msgpack.FormatError, msgpack.StackError):
        return PARSE_ERROR


def format_msgpack(data):
    current_line: base.TViewLine = []
    current_line.append(("text", pprint.pformat(data, indent=4)))
    yield current_line


class ViewMsgPack(base.View):
    name = "MsgPack"
    content_types = [
        "application/msgpack",
        "application/x-msgpack",
    ]

    def __call__(self, data, **metadata):
        data = parse_msgpack(data)
        if data is not PARSE_ERROR:
            return "MsgPack", format_msgpack(data)
