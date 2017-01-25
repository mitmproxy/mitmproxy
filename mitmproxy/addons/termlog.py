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
        def determine_outfile():
            if log.log_tier(e.level) == log.log_tier("error"):
                self.outfile = sys.stderr
            else:
                self.outfile = sys.stdout
        
        determine_outfile()

        if self.options.verbosity >= log.log_tier(e.level):
            click.secho(
                e.msg,
                file=self.outfile,
                fg=dict(error="red", warn="yellow").get(e.level),
                dim=(e.level == "debug"),
                err=(e.level == "error")
            )
