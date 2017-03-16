import urwid
import blinker
import textwrap

from mitmproxy.tools.console import common


footer = [
    ('heading_key', "enter"), ":edit ",
    ('heading_key', "?"), ":help ",
]


def _mkhelp():
    text = []
    keys = [
        ("enter", "edit option"),
        ("D", "reset all to defaults"),
        ("g", "go to start of list"),
        ("G", "go to end of list"),
        ("w", "save options"),
    ]
    text.extend(common.format_keyvals(keys, key="key", val="text", indent=4))
    return text


help_context = _mkhelp()


def fcol(s, width, attr):
    s = str(s)
    return (
        "fixed",
        width,
        urwid.Text((attr, s))
    )


option_focus_change = blinker.Signal()


class OptionItem(urwid.WidgetWrap):
    def __init__(self, master, opt, focused, namewidth):
        self.master, self.opt, self.focused = master, opt, focused
        self.namewidth = namewidth
        w = self.get_text()
        urwid.WidgetWrap.__init__(self, w)

    def get_text(self):
        val = self.opt.current()
        if self.opt.typespec == bool:
            displayval = "true" if val else "false"
        elif val is None:
            displayval = ""
        else:
            displayval = str(val)

        changed = self.master.options.has_changed(self.opt.name)
        if self.focused:
            valstyle = "option_active_selected" if changed else "option_selected"
        else:
            valstyle = "option_active" if changed else "text"
        return urwid.Columns(
            [
                (
                    self.namewidth,
                    urwid.Text([("title", self.opt.name.ljust(self.namewidth))])
                ),
                urwid.AttrMap(
                    urwid.Padding(
                        urwid.Text([(valstyle, displayval)])
                    ),
                    valstyle
                )
            ],
            dividechars=2
        )

    def selectable(self):
        return True

    def keypress(self, xxx_todo_changeme, key):
        if key == "enter":
            if self.opt.typespec == bool:
                self.master.options.toggler(self.opt.name)()
        else:
            return key


class OptionListWalker(urwid.ListWalker):
    def __init__(self, master):
        self.master = master
        self.index = 0
        self.opts = sorted(master.options.keys())
        self.maxlen = max(len(i) for i in self.opts)

        # Trigger a help text update for the first selected item
        first = self.master.options._options[self.opts[0]]
        option_focus_change.send(first.help)
        self.master.options.changed.connect(self.sig_mod)

    def sig_mod(self, *args, **kwargs):
        self._modified()

    def _get(self, pos):
        name = self.opts[pos]
        opt = self.master.options._options[name]
        return OptionItem(self.master, opt, pos == self.index, self.maxlen)

    def get_focus(self):
        return self._get(self.index), self.index

    def set_focus(self, index):
        name = self.opts[index]
        opt = self.master.options._options[name]
        self.index = index
        option_focus_change.send(opt.help)

    def get_next(self, pos):
        if pos >= len(self.opts) - 1:
            return None, None
        pos = pos + 1
        return self._get(pos), pos

    def get_prev(self, pos):
        pos = pos - 1
        if pos < 0:
            return None, None
        return self._get(pos), pos


class OptionsList(urwid.ListBox):
    def __init__(self, master):
        self.master = master
        self.walker = OptionListWalker(master)
        super().__init__(self.walker)

    def keypress(self, size, key):
        if key == "g":
            self.set_focus(0)
            self.walker._modified()
        elif key == "G":
            self.set_focus(len(self.walker.opts) - 1)
            self.walker._modified()
        else:
            return urwid.ListBox.keypress(self, size, key)


class OptionHelp(urwid.Frame):
    def __init__(self, master):
        self.master = master

        h = urwid.Text("Option Help")
        h = urwid.Padding(h, align="left", width=("relative", 100))

        self.inactive_header = urwid.AttrWrap(h, "heading_inactive")
        self.active_header = urwid.AttrWrap(h, "heading")

        super().__init__(self.widget(""), header=self.inactive_header)
        option_focus_change.connect(self.sig_mod)

    def active(self, val):
        if val:
            self.header = self.active_header
        else:
            self.header = self.inactive_header

    def widget(self, txt):
        cols, _ = self.master.ui.get_cols_rows()
        return urwid.ListBox(
            [urwid.Text(i) for i in textwrap.wrap(txt, cols)]
        )

    def sig_mod(self, txt):
        self.set_body(self.widget(txt))


class Options(urwid.Pile):
    def __init__(self, master):
        oh = OptionHelp(master)
        super().__init__(
            [
                OptionsList(master),
                (5, oh),
            ]
        )
        self.master = master

    def keypress(self, size, key):
        key = common.shortcuts(key)
        if key == "tab":
            self.focus_position = (
                self.focus_position + 1
            ) % len(self.widget_list)
            self.widget_list[1].active(self.focus_position == 1)
            key = None
        elif key == "D":
            self.master.options.reset()
            key = None

        # This is essentially a copypasta from urwid.Pile's keypress handler.
        # So much for "closed for modification, but open for extension".
        item_rows = None
        if len(size) == 2:
            item_rows = self.get_item_rows(size, focus = True)
        i = self.widget_list.index(self.focus_item)
        tsize = self.get_item_size(size, i, True, item_rows)
        return self.focus_item.keypress(tsize, key)

