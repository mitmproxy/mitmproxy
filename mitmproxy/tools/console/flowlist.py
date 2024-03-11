from functools import lru_cache

import urwid

import mitmproxy.tools.console.master
from mitmproxy.tools.console import common
from mitmproxy.tools.console import layoutwidget


class FlowItem(urwid.WidgetWrap):
    def __init__(self, master, flow):
        self.master, self.flow = master, flow
        w = self.get_text()
        urwid.WidgetWrap.__init__(self, w)

    def get_text(self):
        cols, _ = self.master.ui.get_cols_rows()
        layout = self.master.options.console_flowlist_layout
        if layout == "list" or (layout == "default" and cols < 100):
            render_mode = common.RenderMode.LIST
        else:
            render_mode = common.RenderMode.TABLE

        return common.format_flow(
            self.flow,
            render_mode=render_mode,
            focused=self.flow is self.master.view.focus.flow,
            hostheader=self.master.options.showhost,
        )

    def selectable(self):
        return True

    def mouse_event(self, size, event, button, col, row, focus):
        if event == "mouse press" and button == 1:
            self.master.commands.execute("console.view.flow @focus")
            return True

    def keypress(self, size, key):
        return key


class FlowListWalker(urwid.ListWalker):
    master: "mitmproxy.tools.console.master.ConsoleMaster"

    def __init__(self, master):
        self.master = master

    def positions(self, reverse=False):
        # The stub implementation of positions can go once this issue is resolved:
        # https://github.com/urwid/urwid/issues/294
        ret = range(self.master.view.get_length())
        if reverse:
            return reversed(ret)
        return ret

    def view_changed(self):
        self._modified()
        self._get.cache_clear()

    def get_focus(self):
        if not self.master.view.focus.flow:
            return None, 0
        f = FlowItem(self.master, self.master.view.focus.flow)
        return f, self.master.view.focus.index

    def set_focus(self, index):
        if self.master.commands.execute("view.properties.inbounds %d" % index):
            self.master.view.focus.index = index

    @lru_cache(maxsize=None)
    def _get(self, pos: int) -> tuple[FlowItem | None, int | None]:
        if not self.master.view.inbounds(pos):
            return None, None
        return FlowItem(self.master, self.master.view[pos]), pos

    def get_next(self, pos):
        return self._get(pos + 1)

    def get_prev(self, pos):
        return self._get(pos - 1)


class FlowListBox(urwid.ListBox, layoutwidget.LayoutWidget):
    title = "Flows"
    keyctx = "flowlist"

    def __init__(self, master: "mitmproxy.tools.console.master.ConsoleMaster") -> None:
        self.master: "mitmproxy.tools.console.master.ConsoleMaster" = master
        super().__init__(FlowListWalker(master))
        self.master.options.subscribe(
            self.set_flowlist_layout, ["console_flowlist_layout"]
        )

    def keypress(self, size, key):
        if key == "m_start":
            self.master.commands.execute("view.focus.go 0")
        elif key == "m_end":
            self.master.commands.execute("view.focus.go -1")
        elif key == "m_select":
            self.master.commands.execute("console.view.flow @focus")
        return urwid.ListBox.keypress(self, size, key)

    def view_changed(self):
        self.body.view_changed()

    def set_flowlist_layout(self, *_) -> None:
        self.master.ui.clear()
