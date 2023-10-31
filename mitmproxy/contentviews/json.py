import json
import re
from collections.abc import Iterator
from functools import lru_cache
from typing import Any

from mitmproxy.contentviews import base

PARSE_ERROR = object()


@lru_cache(1)
def parse_json(s: bytes) -> Any:
    try:
        return json.loads(s.decode("utf-8"))
    except ValueError:
        return PARSE_ERROR


def format_json(data: Any) -> Iterator[base.TViewLine]:
    encoder = json.JSONEncoder(indent=4, sort_keys=True, ensure_ascii=False)
    current_line: base.TViewLine = []
    for chunk in encoder.iterencode(data):
        if "\n" in chunk:
            rest_of_last_line, chunk = chunk.split("\n", maxsplit=1)
            # rest_of_last_line is a delimiter such as , or [
            current_line.append(("text", rest_of_last_line))
            yield current_line
            current_line = []
        if re.match(r'\s*"', chunk):
            if (
                len(current_line) == 1
                and current_line[0][0] == "text"
                and current_line[0][1].isspace()
            ):
                current_line.append(("Token_Name_Tag", chunk))
            else:
                current_line.append(("Token_Literal_String", chunk))
        elif re.match(r"\s*\d", chunk):
            current_line.append(("Token_Literal_Number", chunk))
        elif re.match(r"\s*(true|null|false)", chunk):
            current_line.append(("Token_Keyword_Constant", chunk))
        else:
            current_line.append(("text", chunk))
    yield current_line


class ViewJSON(base.View):
    name = "JSON"

    def __call__(self, data, **metadata):
        data = parse_json(data)
        if data is not PARSE_ERROR:
            return "JSON", format_json(data)

    def render_priority(
        self, data: bytes, *, content_type: str | None = None, **metadata
    ) -> float:
        if not data:
            return 0
        if content_type in (
            "application/json",
            "application/json-rpc",
        ):
            return 1
        if (
            content_type
            and content_type.startswith("application/")
            and content_type.endswith("+json")
        ):
            return 1
        return 0
