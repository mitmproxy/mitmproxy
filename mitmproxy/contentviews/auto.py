from . import api
from mitmproxy import contentviews


class ViewAuto(api.Contentview):
    name = "Auto"

    def prettify(self, data: bytes, metadata: api.Metadata) -> str:
        priority, view = max(
            (v.render_priority(data, metadata), v) for v in contentviews.views
            if not isinstance(v, ViewAuto)
        )
        if priority == 0 and not data:
            return ""
        return view.prettify(data, metadata)

    def render_priority(self, data: bytes, metadata: api.Metadata) -> float:
        return 0
