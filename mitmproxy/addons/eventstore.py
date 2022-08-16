import collections
from typing import Optional

from mitmproxy import command
from mitmproxy.log import LogEntry
from mitmproxy.utils import signals


class EventStore:
    def __init__(self, size=10000):
        self.data: collections.deque[LogEntry] = collections.deque(maxlen=size)
        self.sig_add = signals.SyncSignal()
        self.sig_refresh = signals.SyncSignal()

    @property
    def size(self) -> Optional[int]:
        return self.data.maxlen

    def add_log(self, entry: LogEntry) -> None:
        self.data.append(entry)
        self.sig_add.send(self, entry=entry)

    @command.command("eventstore.clear")
    def clear(self) -> None:
        """
        Clear the event log.
        """
        self.data.clear()
        self.sig_refresh.send(self)
