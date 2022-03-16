import asyncio
import sys


class ErrorCheck:
    """Monitor startup for error log entries, and terminate immediately if there are some."""
    def __init__(self):
        self.has_errored = False

    def add_log(self, e):
        if e.level == "error":
            self.has_errored = True

    async def running(self):
        # don't run immediately, wait for all logging tasks to finish.
        asyncio.create_task(self._shutdown_if_errored())

    async def _shutdown_if_errored(self):
        if self.has_errored:
            sys.exit(1)
