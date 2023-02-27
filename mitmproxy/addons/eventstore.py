import asyncio
import collections
import logging
from collections.abc import Callable

from mitmproxy import command
from mitmproxy import log
from mitmproxy.log import LogEntry
from mitmproxy.utils import signals


class EventStore:
    def __init__(self, size: int = 10000) -> None:
        self.data: collections.deque[LogEntry] = collections.deque(maxlen=size)
        self.sig_add = signals.SyncSignal(lambda entry: None)
        self.sig_refresh = signals.SyncSignal(lambda: None)

        self.logger = CallbackLogger(self._add_log)
        self.logger.install()

    def done(self):
        self.logger.uninstall()

    def _add_log(self, entry: LogEntry) -> None:
        self.data.append(entry)
        self.sig_add.send(entry)

    @property
    def size(self) -> int | None:
        return self.data.maxlen

    @command.command("eventstore.clear")
    def clear(self) -> None:
        """
        Clear the event log.
        """
        self.data.clear()
        self.sig_refresh.send()


class CallbackLogger(log.MitmLogHandler):
    def __init__(
        self,
        callback: Callable[[LogEntry], None],
    ):
        super().__init__()
        self.callback = callback
        self.event_loop = asyncio.get_running_loop()
        self.formatter = log.MitmFormatter(colorize=False)

    def emit(self, record: logging.LogRecord) -> None:
        entry = LogEntry(
            msg=self.format(record),
            level=log.LOGGING_LEVELS_TO_LOGENTRY.get(record.levelno, "error"),
        )
        self.event_loop.call_soon_threadsafe(self.callback, entry)
