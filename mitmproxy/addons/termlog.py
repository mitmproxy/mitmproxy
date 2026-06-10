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
        loader.add_option(
            "termlog_colors",
            str,
            "auto",
            """
            Force-enable or force-disable ANSI color output for log and
            mitmdump flow output. "auto" (default) emits colors only when
            the destination is a TTY. "always" forces colors on, useful when
            piping output to a pager (e.g. `mitmdump | less -R`). "never"
            disables colors unconditionally.
            """,
            choices=("auto", "always", "never"),
        )
        self.logger.setLevel(logging.INFO)

    def configure(self, updated):
        if "termlog_verbosity" in updated:
            self.logger.setLevel(ctx.options.termlog_verbosity.upper())
        if "termlog_colors" in updated:
            self.logger.refresh_color_support(ctx.options.termlog_colors)

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

    def refresh_color_support(self, override: str) -> None:
        """Re-evaluate VT-code support honoring the user's color override.

        Called from TermLog.configure when termlog_colors changes so the
        formatter reflects the new setting without restarting the addon.
        """
        # Validated by the option's `choices` tuple, so the cast is safe.
        self.has_vt_codes = vt_codes.ensure_supported(
            self.file,
            override=override,  # type: ignore[arg-type]
        )
        self.formatter = log.MitmFormatter(self.has_vt_codes)

    def emit(self, record: logging.LogRecord) -> None:
        try:
            print(self.format(record), file=self.file)
        except OSError:
            # We cannot print, exit immediately.
            # See https://github.com/mitmproxy/mitmproxy/issues/4669
            sys.exit(1)
