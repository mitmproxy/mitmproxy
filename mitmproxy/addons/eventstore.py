import collections
import typing  # noqa

import blinker

from mitmproxy import command
from mitmproxy.log import LogEntry


class EventStore:
    def __init__(self, size=10000):
        self.data: typing.Deque[LogEntry] = collections.deque(maxlen=size)
        self.sig_add = blinker.Signal()
        self.sig_refresh = blinker.Signal()

    @property
    def size(self) -> typing.Optional[int]:
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
