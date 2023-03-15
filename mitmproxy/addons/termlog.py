from __future__ import annotations
import asyncio
import logging
from typing import IO

import sys

from mitmproxy import ctx, log
from mitmproxy.utils import vt_codes


class TermLog:
    def __init__(
        self,
        out: IO[str] | None = None
    ):
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

    def done(self):
        t = self._teardown()
        try:
            # try to delay teardown a bit.
            asyncio.create_task(t)
        except RuntimeError:
            # no event loop, we're in a test.
            asyncio.run(t)

    async def _teardown(self):
        self.logger.uninstall()


class TermLogHandler(log.MitmLogHandler):
    def __init__(
        self,
        out: IO[str] | None = None
    ):
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
