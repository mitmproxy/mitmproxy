# Copyright (C) 2012  Aldo Cortesi
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import copy
import urwid
import common
from .. import utils


def _mkhelp():
    text = []
    keys = [
        ("A", "insert row before cursor"),
        ("a", "add row after cursor"),
        ("d", "delete row"),
        ("e", "spawn external editor on current field"),
        ("q", "return to flow view"),
        ("esc", "return to flow view/exit field edit mode"),
        ("tab", "next field"),
        ("enter", "edit field"),
    ]
    text.extend(common.format_keyvals(keys, key="key", val="text", indent=4))
    return text
help_context = _mkhelp()


class SText(common.WWrap):
    def __init__(self, txt, focused):
        w = urwid.Text(txt, wrap="any")
        if focused:
            w = urwid.AttrWrap(w, "focusfield")
        common.WWrap.__init__(self, w)

    def get_text(self):
        return self.w.get_text()[0]

    def keypress(self, size, key):
        return key

    def selectable(self):
        return True


class SEdit(common.WWrap):
    def __init__(self, txt):
        w = urwid.Edit(edit_text=txt, wrap="any", multiline=True)
        w = urwid.AttrWrap(w, "editfield")
        common.WWrap.__init__(self, w)

    def get_text(self):
        return self.w.get_text()[0]

    def selectable(self):
        return True


class KVItem(common.WWrap):
    def __init__(self, focused, editing, maxk, k, v):
        self.focused, self.editing, self.maxk = focused, editing, maxk
        if focused == 0 and editing:
            self.editing = self.kf = SEdit(k)
        else:
            self.kf = SText(k, True if focused == 0 else False)

        if focused == 1 and editing:
            self.editing = self.vf = SEdit(v)
        else:
            self.vf = SText(v, True if focused == 1 else False)

        w = urwid.Columns(
            [
                ("fixed", maxk + 2, self.kf),
                self.vf
            ],
            dividechars = 2
        )
        if focused is not None:
            w.set_focus_column(focused)
        common.WWrap.__init__(self, w)

    def get_kv(self):
        return (self.kf.get_text(), self.vf.get_text())

    def keypress(self, s, k):
        if self.editing:
            k = self.editing.keypress((s[0]-self.maxk-4,), k)
        return k

    def selectable(self):
        return True


KEY_MAX = 30
class KVWalker(urwid.ListWalker):
    def __init__(self, lst, editor):
        self.lst, self.editor = lst, editor
        self.maxk = min(max(len(v[0]) for v in lst), KEY_MAX) if lst else 20
        if self.maxk < 20:
            self.maxk = 20
        self.focus = 0
        self.focus_col = 0
        self.editing = False

    def _modified(self):
        self.editor.show_empty_msg()
        return urwid.ListWalker._modified(self)

    def get_current_value(self):
        if self.lst:
            return self.lst[self.focus][self.focus_col]

    def set_current_value(self, val):
        row = list(self.lst[self.focus])
        row[self.focus_col] = val
        self.lst[self.focus] = tuple(row)

    def delete_focus(self):
        if self.lst:
            del self.lst[self.focus]
            self.focus = min(len(self.lst)-1, self.focus)
            self._modified()

    def _insert(self, pos):
        self.focus = pos
        self.lst.insert(self.focus, ("", ""))
        self.focus_col = 0
        self.start_edit()

    def insert(self):
        return self._insert(self.focus)

    def add(self):
        return self._insert(min(self.focus + 1, len(self.lst)))

    def start_edit(self):
        if self.lst:
            self.editing = KVItem(self.focus_col, True, self.maxk, *self.lst[self.focus])
            self._modified()

    def stop_edit(self):
        if self.editing:
            self.lst[self.focus] = self.editing.get_kv()
            self.editing = False
            self._modified()

    def left(self):
        self.focus_col = 0
        self._modified()

    def right(self):
        self.focus_col = 1
        self._modified()

    def tab_next(self):
        self.stop_edit()
        if self.focus_col == 0:
            self.focus_col = 1
        elif self.focus != len(self.lst)-1:
            self.focus_col = 0
            self.focus += 1
        self._modified()

    def get_focus(self):
        if self.editing:
            return self.editing, self.focus
        elif self.lst:
            return KVItem(self.focus_col, False, self.maxk, *self.lst[self.focus]), self.focus
        else:
            return None, None

    def set_focus(self, focus):
        self.stop_edit()
        self.focus = focus

    def get_next(self, pos):
        if pos+1 >= len(self.lst):
            return None, None
        return KVItem(None, False, self.maxk, *self.lst[pos+1]), pos+1

    def get_prev(self, pos):
        if pos-1 < 0:
            return None, None
        return KVItem(None, False, self.maxk, *self.lst[pos-1]), pos-1


class KVListBox(urwid.ListBox):
    def __init__(self, lw):
        urwid.ListBox.__init__(self, lw)


class KVEditor(common.WWrap):
    def __init__(self, master, title, value, callback, *cb_args, **cb_kwargs):
        value = copy.deepcopy(value)
        self.master, self.title, self.value, self.callback = master, title, value, callback
        self.cb_args, self.cb_kwargs = cb_args, cb_kwargs
        p = urwid.Text(title)
        p = urwid.Padding(p, align="left", width=("relative", 100))
        p = urwid.AttrWrap(p, "heading")
        self.walker = KVWalker(self.value, self)
        self.lb = KVListBox(self.walker)
        self.w = urwid.Frame(self.lb, header = p)
        self.master.statusbar.update("")
        self.show_empty_msg()

    def show_empty_msg(self):
        if self.walker.lst:
            self.w.set_footer(None)
        else:
            self.w.set_footer(
                urwid.Text(
                    [
                        ("highlight", "No values. Press "),
                        ("key", "a"),
                        ("highlight", " to add some."),
                    ]
                )
            )

    def keypress(self, size, key):
        if self.walker.editing:
            if key in ["esc", "enter"]:
                self.walker.stop_edit()
            elif key == "tab":
                pf, pfc = self.walker.focus, self.walker.focus_col
                self.walker.tab_next()
                if self.walker.focus == pf and self.walker.focus_col != pfc:
                    self.walker.start_edit()
            else:
                self.w.keypress(size, key)
            return None

        key = common.shortcuts(key)
        if key in ["q", "esc"]:
            self.callback(self.walker.lst, *self.cb_args, **self.cb_kwargs)
            self.master.pop_view()
        elif key in ["h", "left"]:
            self.walker.left()
        elif key in ["l", "right"]:
            self.walker.right()
        elif key == "tab":
            self.walker.tab_next()
        elif key == "a":
            self.walker.add()
        elif key == "A":
            self.walker.insert()
        elif key == "d":
            self.walker.delete_focus()
        elif key == "e":
            o = self.walker.get_current_value()
            if o is not None:
                n = self.master.spawn_editor(o)
                n = utils.clean_hanging_newline(n)
                self.walker.set_current_value(n)
                self.walker._modified()
        elif key in ["enter"]:
            self.walker.start_edit()
        else:
            return self.w.keypress(size, key)
