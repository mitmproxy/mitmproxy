from mitmproxy import contentviews
from mitmproxy.net import http
from mitmproxy.utils import strutils
from . import base


class ViewAuto(base.View):
    name = "Auto"

    def __call__(self, data, **metadata):
        headers = metadata.get("headers", {})
        ctype = headers.get("content-type")
        if data and ctype:
            ct = http.parse_content_type(ctype) if ctype else None
            ct = "%s/%s" % (ct[0], ct[1])
            preferred_view = next((v for v in contentviews.views if v.should_render(ct)), None)
            if preferred_view:
                return preferred_view(data, **metadata)
            elif strutils.is_xml(data):
                return contentviews.get("XML/HTML")(data, **metadata)
        if metadata.get("query"):
            return contentviews.get("Query")(data, **metadata)
        if data and strutils.is_mostly_bin(data):
            return contentviews.get("Hex")(data)
        if not data:
            return "No content", []
        return contentviews.get("Raw")(data)
