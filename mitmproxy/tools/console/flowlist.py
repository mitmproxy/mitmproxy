import urwid

from mitmproxy.tools.console import common
from mitmproxy.tools.console import layoutwidget
import mitmproxy.tools.console.master # noqa


class FlowItem(urwid.WidgetWrap):

    def __init__(self, master, flow):
        self.master, self.flow = master, flow
        w = self.get_text()
        urwid.WidgetWrap.__init__(self, w)

    def get_text(self):
        cols, _ = self.master.ui.get_cols_rows()
        return common.format_flow(
            self.flow,
            self.flow is self.master.view.focus.flow,
            hostheader=self.master.options.showhost,
            max_url_len=cols,
        )

    def selectable(self):
        return True

    def mouse_event(self, size, event, button, col, row, focus):
        if event == "mouse press" and button == 1:
            if self.flow.request:
                self.master.commands.execute("console.view.flow @focus")
                return True

    def keypress(self, size, key):
        return key


class FlowListWalker(urwid.ListWalker):

    def __init__(self, master):
        self.master = master

    def positions(self, reverse=False):
        # The stub implementation of positions can go once this issue is resolved:
        # https://github.com/urwid/urwid/issues/294
        ret = range(len(self.master.view))
        if reverse:
            return reversed(ret)
        return ret

    def view_changed(self):
        self._modified()

    def get_focus(self):
        if not self.master.view.focus.flow:
            return None, 0
        f = FlowItem(self.master, self.master.view.focus.flow)
        return f, self.master.view.focus.index

    def set_focus(self, index):
        if self.master.view.inbounds(index):
            self.master.view.focus.index = index

    def get_next(self, pos):
        pos = pos + 1
        if not self.master.view.inbounds(pos):
            return None, None
        f = FlowItem(self.master, self.master.view[pos])
        return f, pos

    def get_prev(self, pos):
        pos = pos - 1
        if not self.master.view.inbounds(pos):
            return None, None
        f = FlowItem(self.master, self.master.view[pos])
        return f, pos


class FlowListBox(urwid.ListBox, layoutwidget.LayoutWidget):
    title = "Flows"
    keyctx = "flowlist"

    def __init__(
        self, master: "mitmproxy.tools.console.master.ConsoleMaster"
    ) -> None:
        self.master: "mitmproxy.tools.console.master.ConsoleMaster" = master
        super().__init__(FlowListWalker(master))

    def keypress(self, size, key):
        if key == "m_start":
            self.master.commands.execute("view.go 0")
        elif key == "m_end":
            self.master.commands.execute("view.go -1")
        elif key == "m_select":
            self.master.commands.execute("console.view.flow @focus")
        return urwid.ListBox.keypress(self, size, key)

    def view_changed(self):
        self.body.view_changed()
