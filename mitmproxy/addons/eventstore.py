from typing import List  # noqa

import blinker
from mitmproxy.log import LogEntry


class EventStore:
    def __init__(self):
        self.data = []  # type: List[LogEntry]
        self.sig_add = blinker.Signal()
        self.sig_refresh = blinker.Signal()

    def log(self, entry: LogEntry):
        self.data.append(entry)
        self.sig_add.send(self, entry=entry)

    def clear(self):
        self.data.clear()
        self.sig_refresh.send(self)
