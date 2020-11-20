from mitmproxy.net import http
from mitmproxy.coretypes import multidict
from . import base


class ViewMultipart(base.View):
    name = "Multipart Form"
    content_types = ["multipart/form-data"]

    @staticmethod
    def _format(v):
        yield [("highlight", "Form data:\n")]
        yield from base.format_dict(multidict.MultiDict(v))

    def __call__(self, data, **metadata):
        headers = metadata.get("headers", {})
        v = http.multipart.decode(headers, data)
        if v:
            return "Multipart form", self._format(v)
