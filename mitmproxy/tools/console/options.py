import urwid
import blinker
import textwrap
import pprint
from typing import Optional, Sequence

from mitmproxy import exceptions
from mitmproxy import optmanager
from mitmproxy.tools.console import layoutwidget
from mitmproxy.tools.console import signals
from mitmproxy.tools.console import overlay

HELP_HEIGHT = 5


def can_edit_inplace(opt):
    if opt.choices:
        return False
    if opt.typespec in [str, int, Optional[str], Optional[int]]:
        return True


def fcol(s, width, attr):
    s = str(s)
    return (
        "fixed",
        width,
        urwid.Text((attr, s))
    )


option_focus_change = blinker.Signal()


class OptionItem(urwid.WidgetWrap):
    def __init__(self, walker, opt, focused, namewidth, editing):
        self.walker, self.opt, self.focused = walker, opt, focused
        self.namewidth = namewidth
        self.editing = editing
        super().__init__(None)
        self._w = self.get_widget()

    def get_widget(self):
        val = self.opt.current()
        if self.opt.typespec == bool:
            displayval = "true" if val else "false"
        elif not val:
            displayval = ""
        elif self.opt.typespec == Sequence[str]:
            displayval = pprint.pformat(val, indent=1)
        else:
            displayval = str(val)

        changed = self.walker.master.options.has_changed(self.opt.name)
        if self.focused:
            valstyle = "option_active_selected" if changed else "option_selected"
        else:
            valstyle = "option_active" if changed else "text"

        if self.editing:
            valw = urwid.Edit(edit_text=displayval)
        else:
            valw = urwid.AttrMap(
                urwid.Padding(
                    urwid.Text([(valstyle, displayval)])
                ),
                valstyle
            )

        return urwid.Columns(
            [
                (
                    self.namewidth,
                    urwid.Text([("title", self.opt.name.ljust(self.namewidth))])
                ),
                valw
            ],
            dividechars=2,
            focus_column=1
        )

    def get_edit_text(self):
        return self._w[1].get_edit_text()

    def selectable(self):
        return True

    def keypress(self, size, key):
        if self.editing:
            self._w[1].keypress(size, key)
            return
        return key


class OptionListWalker(urwid.ListWalker):
    def __init__(self, master):
        self.master = master

        self.index = 0
        self.focusobj = None

        self.opts = sorted(master.options.keys())
        self.maxlen = max(len(i) for i in self.opts)
        self.editing = False
        self.set_focus(0)
        self.master.options.changed.connect(self.sig_mod)

    def sig_mod(self, *args, **kwargs):
        self.opts = sorted(self.master.options.keys())
        self.maxlen = max(len(i) for i in self.opts)
        self._modified()
        self.set_focus(self.index)

    def start_editing(self):
        self.editing = True
        self.focus_obj = self._get(self.index, True)
        self._modified()

    def stop_editing(self):
        self.editing = False
        self.focus_obj = self._get(self.index, False)
        self.set_focus(self.index)
        self._modified()

    def get_edit_text(self):
        return self.focus_obj.get_edit_text()

    def _get(self, pos, editing):
        name = self.opts[pos]
        opt = self.master.options._options[name]
        return OptionItem(
            self, opt, pos == self.index, self.maxlen, editing
        )

    def get_focus(self):
        return self.focus_obj, self.index

    def set_focus(self, index):
        self.editing = False
        name = self.opts[index]
        opt = self.master.options._options[name]
        self.index = index
        self.focus_obj = self._get(self.index, self.editing)
        option_focus_change.send(opt.help)

    def get_next(self, pos):
        if pos >= len(self.opts) - 1:
            return None, None
        pos = pos + 1
        return self._get(pos, False), pos

    def get_prev(self, pos):
        pos = pos - 1
        if pos < 0:
            return None, None
        return self._get(pos, False), pos


class OptionsList(urwid.ListBox):
    def __init__(self, master):
        self.master = master
        self.walker = OptionListWalker(master)
        super().__init__(self.walker)

    def save_config(self, path):
        try:
            optmanager.save(self.master.options, path)
        except exceptions.OptionsError as e:
            signals.status_message.send(message=str(e))

    def keypress(self, size, key):
        if self.walker.editing:
            if key == "enter":
                foc, idx = self.get_focus()
                v = self.walker.get_edit_text()
                try:
                    d = self.master.options.parse_setval(foc.opt.name, v)
                    self.master.options.update(**{foc.opt.name: d})
                except exceptions.OptionsError as v:
                    signals.status_message.send(message=str(v))
                self.walker.stop_editing()
                return None
            elif key == "esc":
                self.walker.stop_editing()
                return None
        else:
            if key == "m_start":
                self.set_focus(0)
                self.walker._modified()
            elif key == "m_end":
                self.set_focus(len(self.walker.opts) - 1)
                self.walker._modified()
            elif key == "m_select":
                foc, idx = self.get_focus()
                if foc.opt.typespec == bool:
                    self.master.options.toggler(foc.opt.name)()
                    # Bust the focus widget cache
                    self.set_focus(self.walker.index)
                elif can_edit_inplace(foc.opt):
                    self.walker.start_editing()
                    self.walker._modified()
                elif foc.opt.choices:
                    self.master.overlay(
                        overlay.Chooser(
                            self.master,
                            foc.opt.name,
                            foc.opt.choices,
                            foc.opt.current(),
                            self.master.options.setter(foc.opt.name)
                        )
                    )
                elif foc.opt.typespec == Sequence[str]:
                    self.master.overlay(
                        overlay.OptionsOverlay(
                            self.master,
                            foc.opt.name,
                            foc.opt.current(),
                            HELP_HEIGHT + 5
                        ),
                        valign="top"
                    )
                else:
                    raise NotImplementedError()
        return super().keypress(size, key)


class OptionHelp(urwid.Frame):
    def __init__(self, master):
        self.master = master
        super().__init__(self.widget(""))
        self.set_active(False)
        option_focus_change.connect(self.sig_mod)

    def set_active(self, val):
        h = urwid.Text("Option Help")
        style = "heading" if val else "heading_inactive"
        self.header = urwid.AttrWrap(h, style)

    def widget(self, txt):
        cols, _ = self.master.ui.get_cols_rows()
        return urwid.ListBox(
            [urwid.Text(i) for i in textwrap.wrap(txt, cols)]
        )

    def sig_mod(self, txt):
        self.set_body(self.widget(txt))


class Options(urwid.Pile, layoutwidget.LayoutWidget):
    title = "Options"
    keyctx = "options"

    def __init__(self, master):
        oh = OptionHelp(master)
        self.optionslist = OptionsList(master)
        super().__init__(
            [
                self.optionslist,
                (HELP_HEIGHT, oh),
            ]
        )
        self.master = master

    def current_name(self):
        foc, idx = self.optionslist.get_focus()
        return foc.opt.name

    def keypress(self, size, key):
        if key == "m_next":
            self.focus_position = (
                self.focus_position + 1
            ) % len(self.widget_list)
            self.widget_list[1].set_active(self.focus_position == 1)
            key = None

        # This is essentially a copypasta from urwid.Pile's keypress handler.
        # So much for "closed for modification, but open for extension".
        item_rows = None
        if len(size) == 2:
            item_rows = self.get_item_rows(size, focus = True)
        i = self.widget_list.index(self.focus_item)
        tsize = self.get_item_size(size, i, True, item_rows)
        return self.focus_item.keypress(tsize, key)
