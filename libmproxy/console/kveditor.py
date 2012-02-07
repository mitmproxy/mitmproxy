import urwid
import common

class SText(common.WWrap):
    def __init__(self, txt):
        w = urwid.Text(txt, wrap="any")
        w = urwid.AttrWrap(w, "editfield")
        common.WWrap.__init__(self, w)

    def keypress(self, size, key):
        raise ValueError, key
        time.sleep(0.5)
        return key

    def selectable(self):
        return True


class KVEditor(common.WWrap):
    def __init__(self, master, title, value, callback):
        self.master, self.title, self.value, self.callback = master, title, value, callback
        p = urwid.Text(title)
        p = urwid.Padding(p, align="left", width=("relative", 100))
        p = urwid.AttrWrap(p, "heading")
        maxk = max(len(v[0]) for v in value)
        parts = []
        for k, v in value:
            parts.append(
                urwid.Columns(
                    [
                        (
                            "fixed",
                            maxk + 2,
                            SText(k)
                        ),
                        SText(v)
                    ],
                    dividechars = 2
                )
            )
            parts.append(urwid.Text(" "))
        self.lb = urwid.ListBox(parts)
        self.w = urwid.Frame(self.lb, header = p)
        self.master.statusbar.update("")

    def keypress(self, size, key):
        if key == "q":
            self.master.pop_view()
            return None
        if key in ("tab", "enter"):
            cw = self.lb.get_focus()[0]
            col = cw.get_focus_column()
            if col == 0:
                cw.set_focus_column(1)
            else:
                self.lb._keypress_down(size)
                cw = self.lb.get_focus()[0]
                cw.set_focus_column(0)
            return None
        elif key == "ctrl e":
            # Editor
            pass
        elif key == "ctrl r":
            # Revert
            pass
        elif key == "esc":
            self.master.view_connlist()
            return
        return self.w.keypress(size, key)

