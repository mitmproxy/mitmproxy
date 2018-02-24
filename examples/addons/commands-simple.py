from mitmproxy import command
from mitmproxy import ctx


class MyAddon:
    def __init__(self):
        self.num = 0

    @command.command("myaddon.inc")
    def inc(self) -> None:
        self.num += 1
        ctx.log.info("num = %s" % self.num)


addons = [
    MyAddon()
]
