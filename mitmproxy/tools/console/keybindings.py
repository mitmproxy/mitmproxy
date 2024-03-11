import textwrap

import urwid

from mitmproxy.tools.console import layoutwidget
from mitmproxy.tools.console import signals
from mitmproxy.utils import signals as utils_signals

HELP_HEIGHT = 5


class KeyItem(urwid.WidgetWrap):
    def __init__(self, walker, binding, focused):
        self.walker, self.binding, self.focused = walker, binding, focused
        super().__init__(None)
        self._w = self.get_widget()

    def get_widget(self):
        cmd = textwrap.dedent(self.binding.command).strip()
        parts = [
            (4, urwid.Text([("focus", ">> " if self.focused else "   ")])),
            (10, urwid.Text([("title", self.binding.key)])),
            (12, urwid.Text([("highlight", "\n".join(self.binding.contexts))])),
            urwid.Text([("text", cmd)]),
        ]
        return urwid.Columns(parts)

    def get_edit_text(self):
        return self._w[1].get_edit_text()

    def selectable(self):
        return True

    def keypress(self, size, key):
        return key


class KeyListWalker(urwid.ListWalker):
    def __init__(self, master, keybinding_focus_change):
        self.keybinding_focus_change = keybinding_focus_change
        self.master = master

        self.index = 0
        self.focusobj = None
        self.bindings = list(master.keymap.list("all"))
        self.set_focus(0)
        signals.keybindings_change.connect(self.sig_modified)

    def sig_modified(self):
        self.bindings = list(self.master.keymap.list("all"))
        self.set_focus(min(self.index, len(self.bindings) - 1))
        self._modified()

    def get_edit_text(self):
        return self.focus_obj.get_edit_text()

    def _get(self, pos):
        binding = self.bindings[pos]
        return KeyItem(self, binding, pos == self.index)

    def get_focus(self):
        return self.focus_obj, self.index

    def set_focus(self, index):
        binding = self.bindings[index]
        self.index = index
        self.focus_obj = self._get(self.index)
        self.keybinding_focus_change.send(binding.help or "")
        self._modified()

    def get_next(self, pos):
        if pos >= len(self.bindings) - 1:
            return None, None
        pos = pos + 1
        return self._get(pos), pos

    def get_prev(self, pos):
        pos = pos - 1
        if pos < 0:
            return None, None
        return self._get(pos), pos

    def positions(self, reverse=False):
        if reverse:
            return reversed(range(len(self.bindings)))
        else:
            return range(len(self.bindings))


class KeyList(urwid.ListBox):
    def __init__(self, master, keybinding_focus_change):
        self.master = master
        self.walker = KeyListWalker(master, keybinding_focus_change)
        super().__init__(self.walker)

    def keypress(self, size, key):
        if key == "m_select":
            foc, idx = self.get_focus()
            # Act here
        elif key == "m_start":
            self.set_focus(0)
            self.walker._modified()
        elif key == "m_end":
            self.set_focus(len(self.walker.bindings) - 1)
            self.walker._modified()
        return super().keypress(size, key)


class KeyHelp(urwid.Frame):
    def __init__(self, master, keybinding_focus_change):
        self.master = master
        super().__init__(self.widget(""))
        self.set_active(False)
        keybinding_focus_change.connect(self.sig_mod)

    def set_active(self, val):
        h = urwid.Text("Key Binding Help")
        style = "heading" if val else "heading_inactive"
        self.header = urwid.AttrWrap(h, style)

    def widget(self, txt):
        cols, _ = self.master.ui.get_cols_rows()
        return urwid.ListBox([urwid.Text(i) for i in textwrap.wrap(txt, cols)])

    def sig_mod(self, txt):
        self.set_body(self.widget(txt))


class KeyBindings(urwid.Pile, layoutwidget.LayoutWidget):
    title = "Key Bindings"
    keyctx = "keybindings"
    focus_position: int

    def __init__(self, master):
        keybinding_focus_change = utils_signals.SyncSignal(lambda text: None)

        oh = KeyHelp(master, keybinding_focus_change)
        super().__init__(
            [
                KeyList(master, keybinding_focus_change),
                (HELP_HEIGHT, oh),
            ]
        )
        self.master = master

    def get_focused_binding(self):
        if self.focus_position != 0:
            return None
        f = self.widget_list[0]
        return f.walker.get_focus()[0].binding

    def keypress(self, size, key):
        if key == "m_next":
            self.focus_position = (self.focus_position + 1) % len(self.widget_list)
            self.widget_list[1].set_active(self.focus_position == 1)
            key = None

        # This is essentially a copypasta from urwid.Pile's keypress handler.
        # So much for "closed for modification, but open for extension".
        item_rows = None
        if len(size) == 2:
            item_rows = self.get_item_rows(size, focus=True)
        i = self.widget_list.index(self.focus_item)
        tsize = self.get_item_size(size, i, True, item_rows)
        return self.focus_item.keypress(tsize, key)
