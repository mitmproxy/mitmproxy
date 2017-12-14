import urwid
from mitmproxy.tools.console import layoutwidget
from mitmproxy import log

EVENTLOG_SIZE = 10000


class LogBufferWalker(urwid.SimpleListWalker):
    pass


class EventLog(urwid.ListBox, layoutwidget.LayoutWidget):
    keyctx = "eventlog"
    title = "Events"

    def __init__(self, master):
        self.walker = LogBufferWalker([])
        self.master = master
        super().__init__(self.walker)
        master.events.sig_add.connect(self.add_entry)
        master.events.sig_refresh.connect(self.refresh_entries)
        self.refresh_entries(None)

    def load(self, loader):
        loader.add_option(
            "console_focus_follow", bool, False,
            "Focus follows new flows."
        )

    def set_focus(self, index):
        if 0 <= index < len(self.walker):
            super().set_focus(index)

    def keypress(self, size, key):
        if key == "m_end":
            self.set_focus(len(self.walker) - 1)
        elif key == "m_start":
            self.set_focus(0)
        return urwid.ListBox.keypress(self, size, key)

    def add_entry(self, event_store, entry: log.LogEntry):
        if log.log_tier(self.master.options.verbosity) < log.log_tier(entry.level):
            return
        txt = "%s: %s" % (entry.level, str(entry.msg))
        if entry.level in ("error", "warn"):
            e = urwid.Text((entry.level, txt))
        else:
            e = urwid.Text(txt)
        self.walker.append(e)
        if len(self.walker) > EVENTLOG_SIZE:
            self.walker.pop(0)
        if self.master.options.console_focus_follow:
            self.walker.set_focus(len(self.walker) - 1)

    def refresh_entries(self, event_store):
        self.walker[:] = []
        for event in self.master.events.data:
            self.add_entry(None, event)
