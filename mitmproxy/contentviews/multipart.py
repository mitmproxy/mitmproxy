from . import base
from mitmproxy.coretypes import multidict
from mitmproxy.net.http import multipart


class ViewMultipart(base.View):
    name = "Multipart Form"

    @staticmethod
    def _format(v):
        yield [("highlight", "Form data:\n")]
        yield from base.format_dict(multidict.MultiDict(v))

    def __call__(self, data: bytes, content_type: str | None = None, **metadata):
        if content_type is None:
            return
        v = multipart.decode_multipart(content_type, data)
        if v:
            return "Multipart form", self._format(v)

    def render_priority(
        self, data: bytes, *, content_type: str | None = None, **metadata
    ) -> float:
        return float(bool(data) and content_type == "multipart/form-data")
