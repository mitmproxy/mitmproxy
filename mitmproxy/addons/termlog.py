import click

from mitmproxy import log


class TermLog:
    def __init__(self):
        self.options = None

    def configure(self, options, updated):
        self.options = options

    def log(self, e):
        if self.options.verbosity >= log.log_tier(e.level):
            click.secho(
                e.msg,
                file=self.options.tfile,
                fg=dict(error="red", warn="yellow").get(e.level),
                dim=(e.level == "debug"),
                err=(e.level == "error")
            )
