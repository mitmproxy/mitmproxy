import time
import urwid
import common

class SText(common.WWrap):
    def __init__(self, txt, focused):
        w = urwid.Text(txt, wrap="any")
        if focused:
            w = urwid.AttrWrap(w, "editfield")
        common.WWrap.__init__(self, w)

    def keypress(self, size, key):
        return key

    def selectable(self):
        return True


class SEdit(common.WWrap):
    def __init__(self, txt):
        w = urwid.Edit(txt, wrap="any")
        common.WWrap.__init__(self, w)

    def selectable(self):
        return True


class KVItem(common.WWrap):
    def __init__(self, focused, editing, maxk, k, v):
        self.focused, self.editing = focused, editing
        if focused == 0 and editing:
            self.kf = SEdit(k)
        else:
            self.kf = SText(k, True if focused == 0 else False)

        if focused == 1 and editing:
            self.vf = SEdit(v)
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

    def keypress(self, s, k):
        if self.editing:
            if self.focused == 0:
                return self.kf.keypress(s, k)
            else:
                return self.vf.keypress(s, k)
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

    def edit(self):
        self.editing = KVItem(self.focus_col, True, self.maxk, *self.lst[self.focus])
        self._modified()

    def left(self):
        self.focus_col = 0
        self._modified()

    def right(self):
        self.focus_col = 1
        self._modified()

    def tab_next(self):
        if self.focus_col == 0:
            self.focus_col = 1
        elif self.focus != len(self.lst)-1:
            self.focus_col = 0
            self.focus += 1
        self._modified()

    def get_focus(self):
        if self.editing:
            return self.editing, self.focus
        else:
            return KVItem(self.focus_col, False, self.maxk, *self.lst[self.focus]), self.focus

    def set_focus(self, focus):
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
    def __init__(self, master, title, value, callback):
        self.master, self.title, self.value, self.callback = master, title, value, callback
        p = urwid.Text(title)
        p = urwid.Padding(p, align="left", width=("relative", 100))
        p = urwid.AttrWrap(p, "heading")
        self.walker = KVWalker(self.value)
        self.lb = KVListBox(self.walker)
        self.w = urwid.Frame(self.lb, header = p)
        self.master.statusbar.update("")

    def keypress(self, size, key):
        if self.walker.editing:
            self.w.keypress(size, key)
            return None
        else:
            key = common.shortcuts(key)
            if key == "q":
                self.master.pop_view()
            elif key == "h":
                self.walker.left()
            elif key == "l":
                self.walker.right()
            elif key == "tab":
                self.walker.tab_next()
            elif key == "enter":
                self.walker.edit()
            elif key == "esc":
                self.master.view_connlist()
            else:
                return self.w.keypress(size, key)
