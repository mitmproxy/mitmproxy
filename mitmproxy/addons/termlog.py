import sys
import click

from mitmproxy import log


class TermLog:
    def __init__(self, outfile=None):
        self.options = None
        self.outfile = outfile

    def configure(self, options, updated):
        self.options = options

    def log(self, e):
        if log.log_tier(e.level) == log.log_tier("error"):
            outfile = self.outfile or sys.stderr
        else:
            outfile = self.outfile or sys.stdout

        if self.options.verbosity >= log.log_tier(e.level):
            click.secho(
                e.msg,
                file=outfile,
                fg=dict(error="red", warn="yellow").get(e.level),
                dim=(e.level == "debug"),
                err=(e.level == "error")
            )
