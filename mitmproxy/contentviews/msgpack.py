import typing

import msgpack


from mitmproxy.contentviews import base

PARSE_ERROR = object()


def parse_msgpack(s: bytes) -> typing.Any:
    try:
        return msgpack.unpackb(s, raw=False)
    except (ValueError, msgpack.ExtraData, msgpack.FormatError, msgpack.StackError):
        return PARSE_ERROR


def pretty(value, htchar="    ", lfchar="\n", indent=0):
    nlch = lfchar + htchar * (indent + 1)
    if type(value) is dict:
        items = [
            nlch + repr(key) + ": " + pretty(value[key], htchar, lfchar, indent + 1)
            for key in value
        ]
        return "{%s}" % (",".join(items) + lfchar + htchar * indent)
    elif type(value) is list:
        items = [
            nlch + pretty(item, htchar, lfchar, indent + 1)
            for item in value
        ]
        return "[%s]" % (",".join(items) + lfchar + htchar * indent)
    else:
        return repr(value)


def format_msgpack(data):
    return base.format_text(pretty(data))


class ViewMsgPack(base.View):
    name = "MsgPack"
    __content_types = (
        "application/msgpack",
        "application/x-msgpack",
    )

    def __call__(self, data, **metadata):
        data = parse_msgpack(data)
        if data is not PARSE_ERROR:
            return "MsgPack", format_msgpack(data)

    def render_priority(self, data: bytes, *, content_type: typing.Optional[str] = None, **metadata) -> float:
        return float(content_type in self.__content_types)
