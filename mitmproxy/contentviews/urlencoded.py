from . import base
from mitmproxy.net.http import url


class ViewURLEncoded(base.View):
    name = "URL-encoded"

    def __call__(self, data, **metadata):
        try:
            data = data.decode("ascii", "strict")
        except ValueError:
            return None
        d = url.decode(data)
        return "URLEncoded form", base.format_pairs(d)

    def render_priority(
        self, data: bytes, *, content_type: str | None = None, **metadata
    ) -> float:
        return float(bool(data) and content_type == "application/x-www-form-urlencoded")
