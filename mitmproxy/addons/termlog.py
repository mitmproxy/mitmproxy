import sys
from typing import IO, Optional

from mitmproxy import ctx
from mitmproxy import log
from mitmproxy.contrib import click as miniclick

LOG_COLORS = {'error': "red", 'warn': "yellow", 'alert': "magenta"}


class TermLog:
    def __init__(
        self,
        out: Optional[IO[str]] = None,
        err: Optional[IO[str]] = None,
    ):
        self.out_file: IO[str] = out or sys.stdout
        self.out_isatty = self.out_file.isatty()
        self.err_file: IO[str] = err or sys.stderr
        self.err_isatty = self.err_file.isatty()

    def load(self, loader):
        loader.add_option(
            "termlog_verbosity", str, 'info',
            "Log verbosity.",
            choices=log.LogTierOrder
        )

    def add_log(self, e: log.LogEntry):
        if log.log_tier(ctx.options.termlog_verbosity) >= log.log_tier(e.level):
            if e.level == "error":
                f = self.err_file
                isatty = self.err_isatty
            else:
                f = self.out_file
                isatty = self.out_isatty

            msg = e.msg
            if isatty:
                msg = miniclick.style(
                    e.msg,
                    fg=LOG_COLORS.get(e.level),
                    dim=(e.level == "debug"),
                )
            print(msg, file=f)
