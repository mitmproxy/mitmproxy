from typing import IO, Optional

import click

from mitmproxy import log
from mitmproxy import ctx


class TermLog:
    def __init__(self, outfile=None):
        self.outfile: Optional[IO] = outfile

    def load(self, loader):
        loader.add_option(
            "termlog_verbosity", str, 'info',
            "Log verbosity.",
            choices=log.LogTierOrder
        )

    def add_log(self, e):
        if log.log_tier(ctx.options.termlog_verbosity) >= log.log_tier(e.level):
            click.secho(
                e.msg,
                file=self.outfile,
                fg=dict(error="red", warn="yellow",
                        alert="magenta").get(e.level),
                dim=(e.level == "debug"),
                err=(e.level == "error")
            )
