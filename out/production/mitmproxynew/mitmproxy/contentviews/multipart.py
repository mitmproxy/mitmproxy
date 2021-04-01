from typing import Optional

from mitmproxy.coretypes import multidict
from mitmproxy.net.http import multipart
from . import base


class ViewMultipart(base.View):
    name = "Multipart Form"

    @staticmethod
    def _format(v):
        yield [("highlight", "Form data:\n")]
        yield from base.format_dict(multidict.MultiDict(v))

    def __call__(self, data: bytes, content_type: Optional[str] = None, **metadata):
        if content_type is None:
            return
        v = multipart.decode(content_type, data)
        if v:
            return "Multipart form", self._format(v)

    def render_priority(self, data: bytes, *, content_type: Optional[str] = None, **metadata) -> float:
        return float(content_type == "multipart/form-data")
