
import json
from functools import lru_cache
from typing import Any

from mitmproxy.contentviews._api import Contentview, SyntaxHighlight, Metadata

PARSE_ERROR = object()


@lru_cache(1)
def parse_json(s: bytes) -> Any:
    try:
        return json.loads(s.decode("utf-8"))
    except ValueError:
        return PARSE_ERROR


class JSONContentview(Contentview):
    def prettify(self, data: bytes, metadata: Metadata) -> str:
        data = parse_json(data)
        if data is PARSE_ERROR:
            raise ValueError("Invalid JSON")
        return json.dumps(data, indent=4)

    def render_priority(self, data: bytes, metadata: Metadata) -> float:
        if not data:
            return 0
        if metadata.content_type in (
            "application/json",
            "application/json-rpc",
        ):
            return 1
        if (
            metadata.content_type
            and metadata.content_type.startswith("application/")
            and metadata.content_type.endswith("+json")
        ):
            return 1
        return 0

    @property
    def syntax_highlight(self) -> SyntaxHighlight:
        return "yaml"

json_contentview = JSONContentview()