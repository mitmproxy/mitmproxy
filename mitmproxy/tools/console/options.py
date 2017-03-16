import urwid
import blinker
import textwrap

from mitmproxy.tools.console import common


footer = [
    ('heading_key', "enter/space"), ":toggle ",
    ('heading_key', "C"), ":clear all ",
    ('heading_key', "W"), ":save ",
]


def _mkhelp():
    text = []
    keys = [
        ("enter/space", "activate option"),
        ("C", "clear all options"),
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
        namestyle = "option_selected" if self.focused else "title"
        valstyle = "option_active" if changed else "text"
        return urwid.Columns(
            [
                (
                    self.namewidth,
                    urwid.Text([(namestyle, self.opt.name.ljust(self.namewidth))])
                ),
                urwid.Text([(valstyle, displayval)])
            ],
            dividechars=2
        )

    def selectable(self):
        return True

    def keypress(self, xxx_todo_changeme, key):
        key = common.shortcuts(key)
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
        super().__init__(OptionListWalker(master))


class OptionHelp(urwid.Frame):
    def __init__(self):
        h = urwid.Text("Option Help")
        h = urwid.Padding(h, align="left", width=("relative", 100))
        h = urwid.AttrWrap(h, "heading")
        super().__init__(self.widget(""), header=h)
        option_focus_change.connect(self.sig_mod)

    def selectable(self):
        return False

    def widget(self, txt):
        return urwid.ListBox(
            [urwid.Text(i) for i in textwrap.wrap(txt)]
        )

    def sig_mod(self, txt):
        self.set_body(self.widget(txt))


class Options(urwid.Pile):
    def __init__(self, master):
        oh = OptionHelp()
        super().__init__(
            [
                OptionsList(master),
                (5, oh),
            ]
        )
        self.master = master
