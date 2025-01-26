from __future__ import annotations

import asyncio
import logging
import sys
from typing import IO

from mitmproxy import ctx
from mitmproxy import log
from mitmproxy.utils import vt_codes


class TermLog:
    _teardown_task: asyncio.Task | None = None

    def __init__(self, out: IO[str] | None = None):
        self.logger = TermLogHandler(out)
        self.logger.install()

    def load(self, loader):
        loader.add_option(
            "termlog_verbosity", str, "info", "Log verbosity.", choices=log.LogLevels
        )
        self.logger.setLevel(logging.INFO)

    def configure(self, updated):
        if "termlog_verbosity" in updated:
            self.logger.setLevel(ctx.options.termlog_verbosity.upper())

    def uninstall(self) -> None:
        # uninstall the log dumper.
        # This happens at the very very end after done() is completed,
        # because we don't want to uninstall while other addons are still logging.
        self.logger.uninstall()


class TermLogHandler(log.MitmLogHandler):
    def __init__(self, out: IO[str] | None = None):
        super().__init__()
        self.file: IO[str] = out or sys.stdout
        self.has_vt_codes = vt_codes.ensure_supported(self.file)
        self.formatter = log.MitmFormatter(self.has_vt_codes)

    def emit(self, record: logging.LogRecord) -> None:
        try:
            print(self.format(record), file=self.file)
        except OSError:
            # We cannot print, exit immediately.
            # See https://github.com/mitmproxy/mitmproxy/issues/4669
            sys.exit(1)
