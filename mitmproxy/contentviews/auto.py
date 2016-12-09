from mitmproxy.net import http
from mitmproxy.utils import strutils
from . import base
from mitmproxy.contentviews import get, content_types_map

class ViewAuto(base.View):
    name = "Auto"
    prompt = ("auto", "a")
    content_types = []

    def __call__(self, data, **metadata):
        headers = metadata.get("headers", {})
        ctype = headers.get("content-type")
        if data and ctype:
            ct = http.parse_content_type(ctype) if ctype else None
            ct = "%s/%s" % (ct[0], ct[1])
            if ct in content_types_map:
                return content_types_map[ct][0](data, **metadata)
            elif strutils.is_xml(data):
                return get("XML")(data, **metadata)
        if metadata.get("query"):
            return get("Query")(data, **metadata)
        if data and strutils.is_mostly_bin(data):
            return get("Hex")(data)
        if not data:
            return "No content", []
        return get("Raw")(data)
