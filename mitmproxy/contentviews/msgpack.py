from typing import Any, Optional

import msgpack


from mitmproxy.contentviews import base

PARSE_ERROR = object()


def parse_msgpack(s: bytes) -> Any:
    try:
        return msgpack.unpackb(s, raw=False)
    except (ValueError, msgpack.ExtraData, msgpack.FormatError, msgpack.StackError):
        return PARSE_ERROR


def format_msgpack(data: Any, output = None, indent_count: int = 0) -> list[base.TViewLine]:
    if output is None:
        output = [[]]

    indent = ("text", "    " * indent_count)

    if type(data) is str:
        token = [("Token_Literal_String", f"\"{data}\"")]
        output[-1] += token

        # Need to return if single value, but return is discarded in dict/list loop
        return output

    elif type(data) is float or type(data) is int:
        token = [("Token_Literal_Number", repr(data))]
        output[-1] += token

        return output

    elif type(data) is bool:
        token = [("Token_Keyword_Constant", repr(data))]
        output[-1] += token

        return output

    elif type(data) is dict:
        output[-1] += [("text", "{")]
        for key in data:
            output.append([indent, ("text", "    "), ("Token_Name_Tag", f'"{key}"'), ("text", ": ")])
            format_msgpack(data[key], output, indent_count + 1)

            if key != list(data)[-1]:
                output[-1] += [("text", ",")]

        output.append([indent, ("text", "}")])

        return output

    elif type(data) is list:
        output[-1] += [("text", "[")]
        for item in data:
            output.append([indent, ("text", "    ")])
            format_msgpack(item, output, indent_count + 1)

            if item != data[-1]:
                output[-1] += [("text", ",")]

        output.append([indent, ("text", "]")])

        return output

    else:
        token = [("text", repr(data))]
        output[-1] += token

        return output


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

    def render_priority(
        self, data: bytes, *, content_type: Optional[str] = None, **metadata
    ) -> float:
        return float(bool(data) and content_type in self.__content_types)
