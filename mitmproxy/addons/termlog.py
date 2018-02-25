import sys
import click

from mitmproxy import log
from mitmproxy import ctx

# These get over-ridden by the save execution context. Keep them around so we
# can log directly.
realstdout = sys.stdout
realstderr = sys.stderr


class TermLog:
    def __init__(self, outfile=None):
        self.outfile = outfile

    def load(self, loader):
        loader.add_option(
            "termlog_verbosity", str, 'info',
            "Log verbosity.",
            choices=log.LogTierOrder
        )

    def log(self, e):
        if log.log_tier(e.level) == log.log_tier("error"):
            outfile = self.outfile or realstderr
        else:
            outfile = self.outfile or realstdout

        if log.log_tier(ctx.options.termlog_verbosity) >= log.log_tier(e.level):
            click.secho(
                e.msg,
                file=outfile,
                fg=dict(error="red", warn="yellow",
                        alert="magenta").get(e.level),
                dim=(e.level == "debug"),
                err=(e.level == "error")
            )
