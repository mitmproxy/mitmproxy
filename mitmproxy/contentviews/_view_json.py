import json

from mitmproxy.contentviews._api import Contentview
from mitmproxy.contentviews._api import Metadata


class JSONContentview(Contentview):
    syntax_highlight = "yaml"

    def prettify(self, data: bytes, metadata: Metadata) -> str:
        try:
            parsed = json.loads(data)
            return json.dumps(parsed, indent=4, ensure_ascii=False)
        except (json.JSONDecodeError, UnicodeDecodeError):
            lines = [line.strip() for line in data.splitlines() if line.strip()]
            if not lines:
                raise
            formatted = []
            for line in lines:
                formatted.append(
                    json.dumps(json.loads(line), indent=4, ensure_ascii=False)
                )
            return "\n".join(formatted)

    def render_priority(self, data: bytes, metadata: Metadata) -> float:
        if not data:
            return 0
        if metadata.content_type in (
            "application/json",
            "application/json-rpc",
            "application/x-ndjson",
            "application/ndjson",
        ):
            return 1
        if (
            metadata.content_type
            and metadata.content_type.startswith("application/")
            and (
                metadata.content_type.endswith("json")
                or metadata.content_type.endswith("ndjson")
            )
        ):
            return 1
        return 0


json_view = JSONContentview()
