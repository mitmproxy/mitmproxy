import sys
import click

from mitmproxy import log


class TermLog:
    def __init__(self, outfile=None):
        self.options = None
        self.outfile = outfile or sys.stdout

    def configure(self, options, updated):
        self.options = options

    def log(self, e):
        if self.options.verbosity >= log.log_tier(e.level):
            click.secho(
                e.msg,
                file=self.outfile,
                fg=dict(error="red", warn="yellow").get(e.level),
                dim=(e.level == "debug"),
                err=(e.level == "error")
            )
