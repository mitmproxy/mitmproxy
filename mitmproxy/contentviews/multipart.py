from typing import Optional

from mitmproxy.coretypes import multidict
from mitmproxy.net import http
from . import base
from ..http import HTTPMessage


class ViewMultipart(base.View):
    name = "Multipart Form"

    @staticmethod
    def _format(v):
        yield [("highlight", "Form data:\n")]
        for message in base.format_dict(multidict.MultiDict(v)):
            yield message

    def __call__(self, data: bytes, http_message: Optional[HTTPMessage] = None, **metadata):
        if http_message is None:
            return
        headers = http_message.headers
        v = http.multipart.decode(headers, data)
        if v:
            return "Multipart form", self._format(v)

    def render_priority(self, data: bytes, *, content_type: Optional[str] = None, **metadata) -> float:
        return float(content_type == "multipart/form-data")
