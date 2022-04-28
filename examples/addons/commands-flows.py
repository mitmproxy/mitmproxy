"""Handle flows as command arguments."""
from collections.abc import Sequence

from mitmproxy import command
from mitmproxy import ctx
from mitmproxy import flow
from mitmproxy import http


class MyAddon:
    @command.command("myaddon.addheader")
    def addheader(self, flows: Sequence[flow.Flow]) -> None:
        for f in flows:
            if isinstance(f, http.HTTPFlow):
                f.request.headers["myheader"] = "value"
        ctx.log.alert("done")


addons = [MyAddon()]
