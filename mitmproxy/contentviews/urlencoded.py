from typing import Optional

from mitmproxy.net.http import url
from . import base


class ViewURLEncoded(base.View):
    name = "URL-encoded"

    def __call__(self, data, **metadata):
        try:
            data = data.decode("ascii", "strict")
        except ValueError:
            return None
        d = url.decode(data)
        return "URLEncoded form", base.format_pairs(d)

    def render_priority(self, data: bytes, *, content_type: Optional[str] = None, **metadata) -> float:
        return float(content_type == "application/x-www-form-urlencoded")
