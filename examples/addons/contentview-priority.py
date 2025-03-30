from mitmproxy.contentviews import Contentview, Metadata

class CustomPriority(Contentview):
    def render_priority(self, data: bytes, metadata: Metadata) -> float:
        match metadata.content_type:
            case "application/json":
                return 1.0   # preferred contentview for JSON.
            case "image/png":
                return -1.0  # cannot handle images at all.
            case _:
                return 0.0
