from typing import List  # noqa

from mitmproxy.utils import strutils
from . import base


class ViewASCII(base.View):
    name = "ASCII"

    def __call__(self, data, **metadata):
        style="text"
        from_client=False

        if "from_client" in metadata:
            if metadata['from_client']:
                style="from_client"
                from_client=True
            else:
                style="from_server"

        return "ASCII", base.format_text(strutils.bytes_to_escaped_str(data, True), style=style, from_client=from_client)
