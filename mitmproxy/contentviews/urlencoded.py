from mitmproxy.net.http import url
from . import base


class ViewURLEncoded(base.View):
    name = "URL-encoded"
    content_types = ["application/x-www-form-urlencoded"]

    def __call__(self, data, **metadata):
        try:
            data = data.decode("ascii", "strict")
        except ValueError:
            return None
        d = url.decode(data)
        return "URLEncoded form", base.format_pairs(d)
