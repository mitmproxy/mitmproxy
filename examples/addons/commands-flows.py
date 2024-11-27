"""Handle flows as command arguments."""

import logging
from collections.abc import Sequence

from mitmproxy import command
from mitmproxy import flow
from mitmproxy import http
from mitmproxy.log import ALERT


class MyAddon:
    @command.command("myaddon.addheader")
    def addheader(self, flows: Sequence[flow.Flow]) -> None:
        for f in flows:
            if isinstance(f, http.HTTPFlow):
                f.request.headers["myheader"] = "value"
        logging.log(ALERT, "done")


addons = [MyAddon()]
