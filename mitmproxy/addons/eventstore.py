from typing import List  # noqa

import blinker

from mitmproxy import command
from mitmproxy.log import LogEntry

EVENTLOG_SIZE = 10000


class EventStore:
    def __init__(self):
        self.data = []  # type: List[LogEntry]
        self.sig_add = blinker.Signal()
        self.sig_refresh = blinker.Signal()

    def log(self, entry: LogEntry) -> None:
        self.data.append(entry)
        self.sig_add.send(self, entry=entry)
        # Instead of removing one log row for every row > EVENTLOG_SIZE we add,
        # we accept an overhead of 10% and only purge then to simplify the API.
        if len(self.data) / EVENTLOG_SIZE >= 1.1:
            self.purge()

    def purge(self):
        """Purge event store size to EVENTLOG_SIZE"""
        self.data = self.data[len(self.data) - EVENTLOG_SIZE:]
        self.sig_refresh.send(self)

    @command.command("eventstore.clear")
    def clear(self) -> None:
        """
        Clear the event log.
        """
        self.data.clear()
        self.sig_refresh.send(self)
