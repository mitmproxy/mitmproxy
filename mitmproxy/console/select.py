from __future__ import absolute_import, print_function, division

import urwid

from mitmproxy.console import common


class _OptionWidget(urwid.WidgetWrap):

    def __init__(self, option, text, shortcut, active, focus):
        self.option = option
        textattr = "text"
        keyattr = "key"
        if focus and active:
            textattr = "option_active_selected"
            keyattr = "option_selected_key"
        elif focus:
            textattr = "option_selected"
            keyattr = "option_selected_key"
        elif active:
            textattr = "option_active"
        if shortcut:
            text = common.highlight_key(
                text,
                shortcut,
                textattr = textattr,
                keyattr = keyattr
            )
        opt = urwid.Text(text, align="left")
        opt = urwid.AttrWrap(opt, textattr)
        opt = urwid.Padding(opt, align = "center", width = 40)
        urwid.WidgetWrap.__init__(self, opt)

    def keypress(self, size, key):
        return key

    def selectable(self):
        return True


class OptionWalker(urwid.ListWalker):

    def __init__(self, options):
        urwid.ListWalker.__init__(self)
        self.options = options
        self.focus = 0

    def set_focus(self, pos):
        self.focus = pos

    def get_focus(self):
        return self.options[self.focus].render(True), self.focus

    def get_next(self, pos):
        if pos >= len(self.options) - 1:
            return None, None
        return self.options[pos + 1].render(False), pos + 1

    def get_prev(self, pos):
        if pos <= 0:
            return None, None
        return self.options[pos - 1].render(False), pos - 1


class Heading:

    def __init__(self, text):
        self.text = text

    def render(self, focus):
        opt = urwid.Text("\n" + self.text, align="left")
        opt = urwid.AttrWrap(opt, "title")
        opt = urwid.Padding(opt, align = "center", width = 40)
        return opt


def _neg(*args):
    return False


class Option:

    def __init__(self, text, shortcut, getstate=None, activate=None):
        self.text = text
        self.shortcut = shortcut
        self.getstate = getstate or _neg
        self.activate = activate or _neg

    def render(self, focus):
        return _OptionWidget(
            self,
            self.text,
            self.shortcut,
            self.getstate(),
            focus)


class Select(urwid.ListBox):

    def __init__(self, options):
        self.walker = OptionWalker(options)
        urwid.ListBox.__init__(
            self,
            self.walker
        )
        self.options = options
        self.keymap = {}
        for i in options:
            if hasattr(i, "shortcut") and i.shortcut:
                if i.shortcut in self.keymap:
                    raise ValueError("Duplicate shortcut key: %s" % i.shortcut)
                self.keymap[i.shortcut] = i

    def keypress(self, size, key):
        if key == "enter" or key == " ":
            self.get_focus()[0].option.activate()
            return None
        key = common.shortcuts(key)
        if key in self.keymap:
            self.keymap[key].activate()
            self.set_focus(self.options.index(self.keymap[key]))
            return None
        return super(self.__class__, self).keypress(size, key)
