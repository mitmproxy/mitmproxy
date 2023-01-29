from . import base


class ViewRaw(base.View):
    name = "Raw"

    def __call__(self, data, **metadata):
        return "Raw", base.format_text(data)

    def render_priority(self, data: bytes, **metadata) -> float:
        return 0.1 * float(bool(data))
