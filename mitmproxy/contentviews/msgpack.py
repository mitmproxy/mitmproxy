from typing import Any

import msgpack

from mitmproxy.contentviews import base

PARSE_ERROR = object()


def parse_msgpack(s: bytes) -> Any:
    try:
        return msgpack.unpackb(s, raw=False)
    except (ValueError, msgpack.ExtraData, msgpack.FormatError, msgpack.StackError):
        return PARSE_ERROR


def format_msgpack(
    data: Any, output=None, indent_count: int = 0
) -> list[base.TViewLine]:
    if output is None:
        output = [[]]

    indent = ("text", "    " * indent_count)

    if isinstance(data, str):
        token = [("Token_Literal_String", f'"{data}"')]
        output[-1] += token

        # Need to return if single value, but return is discarded in dict/list loop
        return output

    elif isinstance(data, bool):
        token = [("Token_Keyword_Constant", repr(data))]
        output[-1] += token

        return output

    elif isinstance(data, float | int):
        token = [("Token_Literal_Number", repr(data))]
        output[-1] += token

        return output

    elif isinstance(data, dict):
        output[-1] += [("text", "{")]
        for key in data:
            output.append(
                [
                    indent,
                    ("text", "    "),
                    ("Token_Name_Tag", f'"{key}"'),
                    ("text", ": "),
                ]
            )
            format_msgpack(data[key], output, indent_count + 1)

            if key != list(data)[-1]:
                output[-1] += [("text", ",")]

        output.append([indent, ("text", "}")])

        return output

    elif isinstance(data, list):
        output[-1] += [("text", "[")]

        for count, item in enumerate(data):
            output.append([indent, ("text", "    ")])
            format_msgpack(item, output, indent_count + 1)
            if count != len(data) - 1:
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
        self, data: bytes, *, content_type: str | None = None, **metadata
    ) -> float:
        return float(bool(data) and content_type in self.__content_types)
