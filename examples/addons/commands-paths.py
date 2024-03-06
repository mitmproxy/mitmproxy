"""Handle file paths as command arguments."""

import logging
from collections.abc import Sequence

from mitmproxy import command
from mitmproxy import flow
from mitmproxy import http
from mitmproxy import types
from mitmproxy.log import ALERT


class MyAddon:
    @command.command("myaddon.histogram")
    def histogram(
        self,
        flows: Sequence[flow.Flow],
        path: types.Path,
    ) -> None:
        totals: dict[str, int] = {}
        for f in flows:
            if isinstance(f, http.HTTPFlow):
                totals[f.request.host] = totals.setdefault(f.request.host, 0) + 1

        with open(path, "w+") as fp:
            for cnt, dom in sorted((v, k) for (k, v) in totals.items()):
                fp.write(f"{cnt}: {dom}\n")

        logging.log(ALERT, "done")


addons = [MyAddon()]
