from typing import List  # noqa

from mitmproxy.utils import strutils
from . import base


class ViewRaw(base.View):
    name = "Raw"

    def __call__(self, data, **metadata):
        style="text"

        if "from_client" in metadata:
            if metadata['from_client']:
                style="from_client"
            else:
                style="from_server"
        return "Raw", self._format(data, style, metadata['from_client']) 

    @staticmethod
    def _format(data, style="text", from_client=False):
        indent = ""
        if not from_client:
            indent = "    "
        yield [
            (style, indent + ''.join('{:02x}'.format(x) for x in data))
        ]
