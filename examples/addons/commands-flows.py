import typing

from mitmproxy import command
from mitmproxy import ctx
from mitmproxy import flow


class MyAddon:
    def __init__(self):
        self.num = 0

    @command.command("myaddon.addheader")
    def addheader(self, flows: typing.Sequence[flow.Flow]) -> None:
        for f in flows:
            f.request.headers["myheader"] = "value"
        ctx.log.alert("done")


addons = [
    MyAddon()
]
