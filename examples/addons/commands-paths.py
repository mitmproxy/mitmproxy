"""Handle file paths as command arguments."""
import typing

from mitmproxy import command
from mitmproxy import ctx
from mitmproxy import flow
from mitmproxy import types


class MyAddon:
    @command.command("myaddon.histogram")
    def histogram(
        self,
        flows: typing.Sequence[flow.Flow],
        path: types.Path,
    ) -> None:
        totals = {}
        for f in flows:
            totals[f.request.host] = totals.setdefault(f.request.host, 0) + 1

        with open(path, "w+") as fp:
            for cnt, dom in sorted([(v, k) for (k, v) in totals.items()]):
                fp.write("%s: %s\n" % (cnt, dom))

        ctx.log.alert("done")


addons = [
    MyAddon()
]
