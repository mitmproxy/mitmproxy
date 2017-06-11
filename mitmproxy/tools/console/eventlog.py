import urwid
from mitmproxy.tools.console import signals
from mitmproxy.tools.console import layoutwidget

EVENTLOG_SIZE = 10000


class LogBufferWalker(urwid.SimpleListWalker):
    pass


class EventLog(urwid.ListBox, layoutwidget.LayoutWidget):
    keyctx = "eventlog"
    title = "Events"

    def __init__(self, master):
        self.walker = LogBufferWalker([])
        self.master = master
        urwid.ListBox.__init__(self, self.walker)
        signals.sig_add_log.connect(self.sig_add_log)

    def set_focus(self, index):
        if 0 <= index < len(self.walker):
            super().set_focus(index)

    def keypress(self, size, key):
        if key == "z":
            self.clear_events()
            key = None
        elif key == "m_end":
            self.set_focus(len(self.walker) - 1)
        elif key == "m_start":
            self.set_focus(0)
        return urwid.ListBox.keypress(self, size, key)

    def sig_add_log(self, sender, e, level):
        txt = "%s: %s" % (level, str(e))
        if level in ("error", "warn"):
            e = urwid.Text((level, txt))
        else:
            e = urwid.Text(txt)
        self.walker.append(e)
        if len(self.walker) > EVENTLOG_SIZE:
            self.walker.pop(0)
        if self.master.options.console_focus_follow:
            self.walker.set_focus(len(self.walker) - 1)

    def clear_events(self):
        self.walker[:] = []
