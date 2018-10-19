from mitmproxy.net.http import url
from mitmproxy.coretypes import multidict
from . import base


class ViewURLEncoded(base.View):
    name = "URL-encoded"
    media_types = ["application/x-www-form-urlencoded"]

    def __call__(self, data, **metadata):
        try:
            data = data.decode("ascii", "strict")
        except ValueError:
            return None
        d = url.decode(data)
        return "URLEncoded form", base.format_dict(multidict.MultiDict(d))
