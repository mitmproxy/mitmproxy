import sys
import click

from mitmproxy import log

# These get over-ridden by the save execution context. Keep them around so we
# can log directly.
realstdout = sys.stdout
realstderr = sys.stderr


class TermLog:
    def __init__(self, outfile=None):
        self.options = None
        self.outfile = outfile

    def configure(self, options, updated):
        self.options = options

    def log(self, e):
        if log.log_tier(e.level) == log.log_tier("error"):
            outfile = self.outfile or realstderr
        else:
            outfile = self.outfile or realstdout

        if self.options.verbosity >= log.log_tier(e.level):
            click.secho(
                e.msg,
                file=outfile,
                fg=dict(error="red", warn="yellow").get(e.level),
                dim=(e.level == "debug"),
                err=(e.level == "error")
            )
