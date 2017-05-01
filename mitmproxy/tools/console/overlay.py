import math

import urwid

from mitmproxy.tools.console import common
from mitmproxy.tools.console import signals
from mitmproxy.tools.console import grideditor


class SimpleOverlay(urwid.Overlay):
    def __init__(self, master, widget, parent, width, valign="middle"):
        self.widget = widget
        self.master = master
        super().__init__(
            widget,
            parent,
            align="center",
            width=width,
            valign=valign,
            height="pack"
        )

    def keypress(self, size, key):
        key = super().keypress(size, key)
        if key == "esc":
            signals.pop_view_state.send(self)
        if key == "?":
            self.master.view_help(self.widget.make_help())
        else:
            return key


class Choice(urwid.WidgetWrap):
    def __init__(self, txt, focus, current):
        if current:
            s = "option_active_selected" if focus else "option_active"
        else:
            s = "option_selected" if focus else "text"
        return super().__init__(
            urwid.AttrWrap(
                urwid.Padding(urwid.Text(txt)),
                s,
            )
        )

    def selectable(self):
        return True

    def keypress(self, size, key):
        return key


class ChooserListWalker(urwid.ListWalker):
    def __init__(self, choices, current):
        self.index = 0
        self.choices = choices
        self.current = current

    def _get(self, idx, focus):
        c = self.choices[idx]
        return Choice(c, focus, c == self.current)

    def set_focus(self, index):
        self.index = index

    def get_focus(self):
        return self._get(self.index, True), self.index

    def get_next(self, pos):
        if pos >= len(self.choices) - 1:
            return None, None
        pos = pos + 1
        return self._get(pos, False), pos

    def get_prev(self, pos):
        pos = pos - 1
        if pos < 0:
            return None, None
        return self._get(pos, False), pos


class Chooser(urwid.WidgetWrap):
    def __init__(self, title, choices, current, callback):
        self.choices = choices
        self.callback = callback
        choicewidth = max([len(i) for i in choices])
        self.width = max(choicewidth, len(title)) + 5
        self.walker = ChooserListWalker(choices, current)
        super().__init__(
            urwid.AttrWrap(
                urwid.LineBox(
                    urwid.BoxAdapter(
                        urwid.ListBox(self.walker),
                        len(choices)
                    ),
                    title= title
                ),
                "background"
            )
        )

    def selectable(self):
        return True

    def keypress(self, size, key):
        key = common.shortcuts(key)
        if key == "enter":
            self.callback(self.choices[self.walker.index])
            signals.pop_view_state.send(self)
        return super().keypress(size, key)

    def make_help(self):
        text = []
        keys = [
            ("enter", "choose option"),
            ("esc", "exit chooser"),
        ]
        text.extend(common.format_keyvals(keys, key="key", val="text", indent=4))
        return text


class OptionsOverlay(urwid.WidgetWrap):
    def __init__(self, master, name, vals, vspace):
        """
            vspace: how much vertical space to keep clear
        """
        cols, rows = master.ui.get_cols_rows()
        self.ge = grideditor.OptionsEditor(master, name, vals)
        super().__init__(
            urwid.AttrWrap(
                urwid.LineBox(
                    urwid.BoxAdapter(self.ge, rows - vspace),
                    title=name
                ),
                "background"
            )
        )
        self.width = math.ceil(cols * 0.8)

    def make_help(self):
        return self.ge.make_help()
