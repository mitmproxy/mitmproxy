from . import base
from mitmproxy import contentviews


class ViewAuto(base.View):
    name = "Auto"

    def __call__(self, data, **metadata):
        # TODO: The auto view has little justification now that views implement render_priority,
        # but we keep it around for now to not touch more parts.
        priority, view = max(
            (v.render_priority(data, **metadata), v) for v in contentviews.views
        )
        if priority == 0 and not data:
            return "No content", []
        return view(data, **metadata)

    def render_priority(self, data: bytes, **metadata) -> float:
        return -1  # don't recurse.
