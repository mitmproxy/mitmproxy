import urwid

from mitmproxy.tools.console import common
from mitmproxy.tools.console import layoutwidget
import mitmproxy.tools.console.master # noqa


class FlowItem(urwid.WidgetWrap):

    def __init__(self, master, view, flow):
        self.master, self.view, self.flow = master, view, flow
        w = self.get_text()
        urwid.WidgetWrap.__init__(self, w)

    def get_text(self):
        cols, _ = self.master.ui.get_cols_rows()
        if self.view.flow_type == "http1":
            return common.format_flow(
                self.flow,
                self.flow is self.view.focus.flow,
                hostheader=self.master.options.showhost,
                max_url_len=cols,
            )
        elif self.view.flow_type == "http2":
            return common.format_http2_item(
                self.flow,
                self.flow is self.view.focus.flow,
            )
        else:
            raise NotImplementedError()

    def selectable(self):
        return True

    def mouse_event(self, size, event, button, col, row, focus):
        if event == "mouse press" and button == 1:
            if self.view.flow_type == "http1":
                if self.flow.request:
                    self.master.commands.execute("console.view.flow @focus")
                    return True
            elif self.view.flow_type == "http2":
                    self.master.commands.execute("console.view.flow @focus")
                    return True
            else:
                raise NotImplementedError()
    def keypress(self, size, key):
        return key


class FlowListWalker(urwid.ListWalker):

    def __init__(self, master, view, flt=None):
        self.master, self.view, self.flt = master, view, flt
        if flt:
            self.focus = 1

    def positions(self, reverse=False):
        # The stub implementation of positions can go once this issue is resolved:
        # https://github.com/urwid/urwid/issues/294
        ret = range(self.master.commands.execute("view.%s.properties.length", self.view.flow_type))
        if reverse:
            return reversed(ret)
        return ret

    def view_changed(self):
        self._modified()

    def get_focus(self):
        if not self.flt:
            if not self.view.focus.flow:
                return None, 0
            f = FlowItem(self.master, self.view, self.view.focus.flow)
            return f, self.view.focus.index
        else:
            f = FlowItem(self.master, self.view, self.view[self.focus])
            return f, self.focus

    def set_focus(self, index):
        if not self.flt:
            if self.master.commands.execute("view.%s.properties.inbounds %d" % (self.view.flow_type, index)):
                self.view.focus.index = index
        else:
            self.focus = index

    def get_next(self, pos):
        while True:
            pos = pos + 1
            if not self.master.commands.execute("view.%s.properties.inbounds %d" % (self.view.flow_type, pos)):
                return None, None
            if self.flt:
                if not self.flt(self.view[pos]):
                    continue
            f = FlowItem(self.master, self.view, self.view[pos])
            break
        return f, pos

    def get_prev(self, pos):
        while True:
            pos = pos - 1
            if not self.master.commands.execute("view.%s.properties.inbounds %d" % (self.view.flow_type, pos)):
                return None, None
            if self.flt:
                if self.view[pos].stream_id != 0:
                    continue
            f = FlowItem(self.master, self.view, self.view[pos])
            break
        return f, pos


class FlowListBox(urwid.ListBox, layoutwidget.LayoutWidget):
    def __init__(
        self, master: "mitmproxy.tools.console.master.ConsoleMaster",
        view: "mitmproxy.addons.View",
        flt=None
    ) -> None:
        self.master: "mitmproxy.tools.console.master.ConsoleMaster" = master
        self.view: "mitmproxy.addons.View" = view
        self.title = "Flows %s" % self.view.flow_type
        self.keyctx = "flowlist_%s" % self.view.flow_type
        super().__init__(FlowListWalker(master, view, flt))

    def keypress(self, size, key):
        if key == "m_start":
            self.master.commands.execute("view.%s.focus.go 0" % self.view.flow_type)
        elif key == "m_end":
            self.master.commands.execute("view.%s.focus.go -1" % self.view.flow_type)
        elif key == "m_select":
            self.master.commands.execute("console.view.flow @focus")
        return urwid.ListBox.keypress(self, size, key)

    def view_changed(self):
        self.body.view_changed()
