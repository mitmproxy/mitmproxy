from typing import List  # noqa

from mitmproxy.utils import strutils
from . import base


class ViewRaw(base.View):
    name = "Raw"

    def __call__(self, data, **metadata):
        style="text"
        from_client = False

        if "from_client" in metadata:
            if metadata['from_client']:
                style="from_client"
                from_client = True
            else:
                style="from_server"
                from_client = False

        return "Raw", self._format(data, style, from_client) 

    @staticmethod
    def _format(data, style="text", from_client=False):
        indent = ""
        if not from_client:
            indent = "    "
        yield [
            (style, indent + ''.join('{:02x}'.format(x) for x in data))
        ]
