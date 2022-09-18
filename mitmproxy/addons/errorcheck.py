import asyncio
import logging

import sys

from mitmproxy import log


class ErrorCheck:
    """Monitor startup for error log entries, and terminate immediately if there are some."""

    def __init__(self, log_to_stderr: bool = False):
        self.log_to_stderr = log_to_stderr

        self.logger = ErrorCheckHandler()
        self.logger.install()

    def finish(self):
        self.logger.uninstall()

    async def shutdown_if_errored(self):
        # don't run immediately, wait for all logging tasks to finish.
        await asyncio.sleep(0)
        if self.logger.has_errored:
            if self.log_to_stderr:
                plural = "s" if len(self.logger.has_errored) > 1 else ""
                msg = "\n".join(r.msg for r in self.logger.has_errored)
                print(f"Error{plural} on startup: {msg}", file=sys.stderr)

            sys.exit(1)


class ErrorCheckHandler(log.MitmLogHandler):
    def __init__(self):
        super().__init__(logging.ERROR)
        self.has_errored: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.has_errored.append(record)
