import json

from mitmproxy.contentviews._api import Contentview
from mitmproxy.contentviews._api import Metadata


class JSONContentview(Contentview):
    syntax_highlight = "yaml"

    def prettify(self, data: bytes, metadata: Metadata) -> str:
        data = json.loads(data)
        return json.dumps(data, indent=4, ensure_ascii=False)

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
            and metadata.content_type.endswith("json")
        ):
            return 1
        return 0


json_view = JSONContentview()
