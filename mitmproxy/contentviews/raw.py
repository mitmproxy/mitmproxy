from mitmproxy.utils import strutils
from . import base


class ViewRaw(base.View):
    name = "Raw"
    prompt = ("raw", "r")
    content_types = []

    def __call__(self, data, **metadata):
        return "Raw", base.format_text(strutils.bytes_to_escaped_str(data, True))
