import json
import pathlib
from typing import Optional

from mitmproxy import ctx


class PortFile:
    def load(self, loader):
        loader.add_option(
            name="datadir",
            typespec=Optional[str],
            default=None,
            help="Creates `portfile` mapping proxies (by mode spec) to the port "
            "they use in the provided directory.",
        )

    def running(self):
        if not ctx.options.datadir:
            return

        datadir = pathlib.Path(ctx.options.datadir)
        if not datadir.is_dir():
            ctx.log.warning("%s is not a directory", datadir)
            return

        proxies = ctx.master.addons.get("proxyserver")
        modemap = {
            instance.mode.full_spec: addr[1]
            for instance in proxies.servers
            # assumes all listen_addrs of a given instance are bound
            # to the same port, but as far as I can tell mitmproxy
            # works very hard to try and make it so
            if (addr := next(iter(instance.listen_addrs), None))
        }
        with datadir.joinpath("portfile").open("w", encoding="utf-8") as fp:
            json.dump(modemap, fp)


addons = [PortFile()]
