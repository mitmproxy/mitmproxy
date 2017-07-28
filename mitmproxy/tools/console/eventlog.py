import urwid
from mitmproxy.tools.console import signals
from mitmproxy.tools.console import layoutwidget
from mitmproxy import ctx
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
        urwid.ListBox.__init__(self, self.walker)
        signals.sig_add_log.connect(self.sig_add_log)
        signals.sig_clear_log.connect(self.sig_clear_log)

    def set_focus(self, index):
        if 0 <= index < len(self.walker):
            super().set_focus(index)

    def keypress(self, size, key):
        if key == "m_end":
            self.set_focus(len(self.walker) - 1)
        elif key == "m_start":
            self.set_focus(0)
        return urwid.ListBox.keypress(self, size, key)

    def sig_add_log(self, sender, e, level):
        if log.log_tier(ctx.options.verbosity) < log.log_tier(level):
            return
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

    def sig_clear_log(self, sender):
        self.walker[:] = []
