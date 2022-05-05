import asyncio
import sys

from mitmproxy import log


class ErrorCheck:
    """Monitor startup for error log entries, and terminate immediately if there are some."""

    def __init__(self, log_to_stderr: bool = False):
        self.has_errored: list[str] = []
        self.log_to_stderr = log_to_stderr

    def add_log(self, e: log.LogEntry):
        if e.level == "error":
            self.has_errored.append(e.msg)

    async def running(self):
        # don't run immediately, wait for all logging tasks to finish.
        asyncio.create_task(self._shutdown_if_errored())

    async def _shutdown_if_errored(self):
        if self.has_errored:
            if self.log_to_stderr:
                plural = "s" if len(self.has_errored) > 1 else ""
                msg = "\n".join(self.has_errored)
                print(f"Error{plural} on startup: {msg}", file=sys.stderr)

            sys.exit(1)
