import urwid

from mitmproxy.tools.console import common
from mitmproxy.tools.console import layoutwidget
import mitmproxy.tools.console.master  # noqa


class FlowItem(urwid.WidgetWrap):

    def __init__(self, master, view, item, flt=None):
        self.master, self.view, self.item, self.flt = master, view, item, flt
        w = self.get_text()
        urwid.WidgetWrap.__init__(self, w)

    def get_text(self):
        cols, _ = self.master.ui.get_cols_rows()
        if self.view.flow_type == "http1":
            return common.format_item(
                self.item,
                self.item is self.view.filtred_views_focus[self.flt].item if self.flt else self.item is self.view.focus.item,
                hostheader=self.master.options.showhost,
                max_url_len=cols,
            )
        elif self.view.flow_type == "http2":
            return common.format_http2_item(
                self.item,
                self.item is self.view.filtred_views_focus[self.flt].item if self.flt else self.item is self.view.focus.item,
            )
        else:
            raise exceptions.TypeError("Unknown flow type: %s" % self.view.flow_type)

    def selectable(self):
        return True

    def mouse_event(self, size, event, button, col, row, focus):
        if event == "mouse press" and button == 1:
            if self.flt:
                return
            if self.view.flow_type == "http1":
                if self.item.request:
                    self.master.commands.execute("console.view.item @focus")
                    return True
            elif self.view.flow_type == "http2":
                self.master.commands.execute("console.view.item @focus")
                return True
            else:
                raise exceptions.TypeError("Unknown flow type: %s" % self.view.flow_type)

    def keypress(self, size, key):
        return key


class FlowListWalker(urwid.ListWalker):

    def __init__(self, master, view, flt=None):
        self.master, self.view, self.flt = master, view, flt

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
        if self.flt:
            if not self.view.filtred_views_focus[self.flt].item:
                return None, 0
            i = FlowItem(self.master, self.view, self.view.filtred_views_focus[self.flt].item, self.flt)
        else:
            if not self.view.focus.item:
                return None, 0
            i = FlowItem(self.master, self.view, self.view.focus.item)
        if self.flt:
            return i, self.view.filtred_views_focus[self.flt].index
        else:
            return i, self.view.focus.index

    def set_focus(self, index):
        if self.master.commands.execute("view.%s.properties.inbounds %d %s" % (self.view.flow_type, index, self.flt)):
            if self.flt:
                self.view.filtred_views_focus[self.flt].index = index
            else:
                self.view.focus.index = index

    def get_next(self, pos):
        pos = pos + 1
        if not self.master.commands.execute("view.%s.properties.inbounds %d %s" % (self.view.flow_type, pos, self.flt)):
            return None, None
        if self.flt:
            f = FlowItem(self.master, self.view, self.view.filtred_views[self.flt][pos], self.flt)
        else:
            f = FlowItem(self.master, self.view, self.view[pos])
        return f, pos

    def get_prev(self, pos):
        pos = pos - 1
        if not self.master.commands.execute("view.%s.properties.inbounds %d %s" % (self.view.flow_type, pos, self.flt)):
            return None, None
        if self.flt:
            f = FlowItem(self.master, self.view, self.view.filtred_views[self.flt][pos], self.flt)
        else:
            f = FlowItem(self.master, self.view, self.view[pos])
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
        self.flt = flt
        super().__init__(FlowListWalker(master, view, flt))

    def keypress(self, size, key):
        if key == "m_start":
            self.master.commands.execute("view.%s.focus.go 0" % self.view.flow_type)
        elif key == "m_end":
            self.master.commands.execute("view.%s.focus.go -1" % self.view.flow_type)
        elif key == "m_select":
            if self.flt:
                return
            self.master.commands.execute("console.view.item @focus")
        return urwid.ListBox.keypress(self, size, key)

    def view_changed(self):
        self.body.view_changed()
