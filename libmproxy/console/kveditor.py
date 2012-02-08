import copy
import urwid
import common

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


class KVWalker(urwid.ListWalker):
    def __init__(self, lst):
        self.lst = lst
        self.maxk = max(len(v[0]) for v in lst)
        self.focus = 0
        self.focus_col = 0
        self.editing = False

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
        self.walker = KVWalker(self.value)
        self.lb = KVListBox(self.walker)
        self.w = urwid.Frame(self.lb, header = p)
        self.master.statusbar.update("")

    def keypress(self, size, key):
        if self.walker.editing:
            if key in ["esc", "enter"]:
                self.walker.stop_edit()
            elif key == "tab":
                pf = self.walker.focus
                self.walker.tab_next()
                if self.walker.focus == pf:
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
        elif key == "i":
            self.walker.insert()
        elif key == "d":
            self.walker.delete_focus()
        elif key in ["enter", "e"]:
            self.walker.start_edit()
        else:
            return self.w.keypress(size, key)
