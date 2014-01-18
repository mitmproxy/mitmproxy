import copy, re, os
import urwid
import common
from .. import utils, filt, script
from netlib import http_uastrings


footer = [
    ('heading_key', "enter"), ":edit ",
    ('heading_key', "q"), ":back ",
]
footer_editing = [
    ('heading_key', "esc"), ":stop editing ",
]


class SText(common.WWrap):
    def __init__(self, txt, focused, error):
        txt = txt.encode("string-escape")
        w = urwid.Text(txt, wrap="any")
        if focused:
            if error:
                w = urwid.AttrWrap(w, "focusfield_error")
            else:
                w = urwid.AttrWrap(w, "focusfield")
        elif error:
            w = urwid.AttrWrap(w, "field_error")
        common.WWrap.__init__(self, w)

    def get_text(self):
        return self.w.get_text()[0]

    def keypress(self, size, key):
        return key

    def selectable(self):
        return True


class SEdit(common.WWrap):
    def __init__(self, txt):
        txt = txt.encode("string-escape")
        w = urwid.Edit(edit_text=txt, wrap="any", multiline=True)
        w = urwid.AttrWrap(w, "editfield")
        common.WWrap.__init__(self, w)

    def get_text(self):
        return self.w.get_text()[0]

    def selectable(self):
        return True


class GridRow(common.WWrap):
    def __init__(self, focused, editing, editor, values):
        self.focused, self.editing, self.editor = focused, editing, editor

        errors = values[1]
        self.fields = []
        for i, v in enumerate(values[0]):
            if focused == i and editing:
                self.editing = SEdit(v)
                self.fields.append(self.editing)
            else:
                self.fields.append(
                    SText(v, True if focused == i else False, i in errors)
                )

        fspecs = self.fields[:]
        if len(self.fields) > 1:
            fspecs[0] = ("fixed", self.editor.first_width + 2, fspecs[0])
        w = urwid.Columns(
            fspecs,
            dividechars = 2
        )
        if focused is not None:
            w.set_focus_column(focused)
        common.WWrap.__init__(self, w)

    def get_edit_value(self):
        return self.editing.get_text()

    def keypress(self, s, k):
        if self.editing:
            w = self.w.column_widths(s)[self.focused]
            k = self.editing.keypress((w,), k)
        return k

    def selectable(self):
        return True


class GridWalker(urwid.ListWalker):
    """
        Stores rows as a list of (rows, errors) tuples, where rows is a list
        and errors is a set with an entry of each offset in rows that is an
        error.
    """
    def __init__(self, lst, editor):
        self.lst = [(i, set([])) for i in lst]
        self.editor = editor
        self.focus = 0
        self.focus_col = 0
        self.editing = False

    def _modified(self):
        self.editor.show_empty_msg()
        return urwid.ListWalker._modified(self)

    def add_value(self, lst):
        self.lst.append((lst[:], set([])))
        self._modified()

    def get_current_value(self):
        if self.lst:
            return self.lst[self.focus][0][self.focus_col]

    def set_current_value(self, val, unescaped):
        if not unescaped:
            try:
                val = val.decode("string-escape")
            except ValueError:
                self.editor.master.statusbar.message("Invalid Python-style string encoding.", 1000)
                return

        errors = self.lst[self.focus][1]
        emsg = self.editor.is_error(self.focus_col, val)
        if emsg:
            self.editor.master.statusbar.message(emsg, 1000)
            errors.add(self.focus_col)

        row = list(self.lst[self.focus][0])
        row[self.focus_col] = val
        self.lst[self.focus] = [tuple(row), errors]

    def delete_focus(self):
        if self.lst:
            del self.lst[self.focus]
            self.focus = min(len(self.lst)-1, self.focus)
            self._modified()

    def _insert(self, pos):
        self.focus = pos
        self.lst.insert(self.focus, [[""]*self.editor.columns, set([])])
        self.focus_col = 0
        self.start_edit()

    def insert(self):
        return self._insert(self.focus)

    def add(self):
        return self._insert(min(self.focus + 1, len(self.lst)))

    def start_edit(self):
        if self.lst:
            self.editing = GridRow(self.focus_col, True, self.editor, self.lst[self.focus])
            self.editor.master.statusbar.update(footer_editing)
            self._modified()

    def stop_edit(self):
        if self.editing:
            self.editor.master.statusbar.update(footer)
            self.set_current_value(self.editing.get_edit_value(), False)
            self.editing = False
            self._modified()

    def left(self):
        self.focus_col = max(self.focus_col - 1, 0)
        self._modified()

    def right(self):
        self.focus_col = min(self.focus_col + 1, self.editor.columns-1)
        self._modified()

    def tab_next(self):
        self.stop_edit()
        if self.focus_col < self.editor.columns-1:
            self.focus_col += 1
        elif self.focus != len(self.lst)-1:
            self.focus_col = 0
            self.focus += 1
        self._modified()

    def get_focus(self):
        if self.editing:
            return self.editing, self.focus
        elif self.lst:
            return GridRow(self.focus_col, False, self.editor, self.lst[self.focus]), self.focus
        else:
            return None, None

    def set_focus(self, focus):
        self.stop_edit()
        self.focus = focus

    def get_next(self, pos):
        if pos+1 >= len(self.lst):
            return None, None
        return GridRow(None, False, self.editor, self.lst[pos+1]), pos+1

    def get_prev(self, pos):
        if pos-1 < 0:
            return None, None
        return GridRow(None, False, self.editor, self.lst[pos-1]), pos-1


class GridListBox(urwid.ListBox):
    def __init__(self, lw):
        urwid.ListBox.__init__(self, lw)


FIRST_WIDTH_MAX = 40
FIRST_WIDTH_MIN = 20
class GridEditor(common.WWrap):
    title = None
    columns = None
    headings = None
    def __init__(self, master, value, callback, *cb_args, **cb_kwargs):
        value = copy.deepcopy(value)
        self.master, self.value, self.callback = master, value, callback
        self.cb_args, self.cb_kwargs = cb_args, cb_kwargs

        first_width = 20
        if value:
            for r in value:
                assert len(r) == self.columns
                first_width = max(len(r), first_width)
        self.first_width = min(first_width, FIRST_WIDTH_MAX)

        title = urwid.Text(self.title)
        title = urwid.Padding(title, align="left", width=("relative", 100))
        title = urwid.AttrWrap(title, "heading")

        headings = []
        for i, h in enumerate(self.headings):
            c = urwid.Text(h)
            if i == 0 and len(self.headings) > 1:
                headings.append(("fixed", first_width + 2, c))
            else:
                headings.append(c)
        h = urwid.Columns(
            headings,
            dividechars = 2
        )
        h = urwid.AttrWrap(h, "heading")

        self.walker = GridWalker(self.value, self)
        self.lb = GridListBox(self.walker)
        self.w = urwid.Frame(
            self.lb,
            header = urwid.Pile([title, h])
        )
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

    def encode(self, s):
        if not self.encoding:
            return s
        try:
            return s.encode(self.encoding)
        except ValueError:
            return None

    def read_file(self, p, unescaped=False):
        if p:
            try:
                p = os.path.expanduser(p)
                d = file(p, "rb").read()
                self.walker.set_current_value(d, unescaped)
                self.walker._modified()
            except IOError, v:
                return str(v)

    def keypress(self, size, key):
        if self.walker.editing:
            if key in ["esc"]:
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
            res = []
            for i in self.walker.lst:
                if not i[1] and any([x.strip() for x in i[0]]):
                    res.append(i[0])
            self.callback(res, *self.cb_args, **self.cb_kwargs)
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
        elif key == "r":
            self.master.path_prompt("Read file: ", "", self.read_file)
        elif key == "R":
            self.master.path_prompt("Read unescaped file: ", "", self.read_file, True)
        elif key == "e":
            o = self.walker.get_current_value()
            if o is not None:
                n = self.master.spawn_editor(o.encode("string-escape"))
                n = utils.clean_hanging_newline(n)
                self.walker.set_current_value(n, False)
                self.walker._modified()
        elif key in ["enter"]:
            self.walker.start_edit()
        elif not self.handle_key(key):
            return self.w.keypress(size, key)

    def is_error(self, col, val):
        """
            Return False, or a string error message.
        """
        return False

    def handle_key(self, key):
        return False

    def make_help(self):
        text = []
        text.append(urwid.Text([("text", "Editor control:\n")]))
        keys = [
            ("A", "insert row before cursor"),
            ("a", "add row after cursor"),
            ("d", "delete row"),
            ("e", "spawn external editor on current field"),
            ("q", "return to flow view"),
            ("r", "read value from file"),
            ("R", "read unescaped value from file"),
            ("esc", "return to flow view/exit field edit mode"),
            ("tab", "next field"),
            ("enter", "edit field"),
        ]
        text.extend(common.format_keyvals(keys, key="key", val="text", indent=4))
        text.append(
            urwid.Text(
                [
                    "\n",
                    ("text", "Values are escaped Python-style strings.\n"),
                ]
            )
        )
        return text


class QueryEditor(GridEditor):
    title = "Editing query"
    columns = 2
    headings = ("Key", "Value")


class HeaderEditor(GridEditor):
    title = "Editing headers"
    columns = 2
    headings = ("Key", "Value")
    def make_help(self):
        h = GridEditor.make_help(self)
        text = []
        text.append(urwid.Text([("text", "Special keys:\n")]))
        keys = [
            ("U", "add User-Agent header"),
        ]
        text.extend(common.format_keyvals(keys, key="key", val="text", indent=4))
        text.append(urwid.Text([("text", "\n")]))
        text.extend(h)
        return text

    def set_user_agent(self, k):
        ua = http_uastrings.get_by_shortcut(k)
        if ua:
            self.walker.add_value(
                [
                    "User-Agent",
                    ua[2]
                ]
            )

    def handle_key(self, key):
        if key == "U":
            self.master.prompt_onekey(
                "Add User-Agent header:",
                [(i[0], i[1]) for i in http_uastrings.UASTRINGS],
                self.set_user_agent,
            )
            return True


class URLEncodedFormEditor(GridEditor):
    title = "Editing URL-encoded form"
    columns = 2
    headings = ("Key", "Value")


class ReplaceEditor(GridEditor):
    title = "Editing replacement patterns"
    columns = 3
    headings = ("Filter", "Regex", "Replacement")
    def is_error(self, col, val):
        if col == 0:
            if not filt.parse(val):
                return "Invalid filter specification."
        elif col == 1:
            try:
                re.compile(val)
            except re.error:
                return "Invalid regular expression."
        return False


class SetHeadersEditor(GridEditor):
    title = "Editing header set patterns"
    columns = 3
    headings = ("Filter", "Header", "Value")
    def is_error(self, col, val):
        if col == 0:
            if not filt.parse(val):
                return "Invalid filter specification"
        return False

    def make_help(self):
        h = GridEditor.make_help(self)
        text = []
        text.append(urwid.Text([("text", "Special keys:\n")]))
        keys = [
            ("U", "add User-Agent header"),
        ]
        text.extend(common.format_keyvals(keys, key="key", val="text", indent=4))
        text.append(urwid.Text([("text", "\n")]))
        text.extend(h)
        return text

    def set_user_agent(self, k):
        ua = http_uastrings.get_by_shortcut(k)
        if ua:
            self.walker.add_value(
                [
                    ".*",
                    "User-Agent",
                    ua[2]
                ]
            )

    def handle_key(self, key):
        if key == "U":
            self.master.prompt_onekey(
                "Add User-Agent header:",
                [(i[0], i[1]) for i in http_uastrings.UASTRINGS],
                self.set_user_agent,
            )
            return True


class PathEditor(GridEditor):
    title = "Editing URL path components"
    columns = 1
    headings = ("Component",)


class ScriptEditor(GridEditor):
    title = "Editing scripts"
    columns = 1
    headings = ("Command",)
    def is_error(self, col, val):
        try:
            script.Script.parse_command(val)
        except script.ScriptError, v:
            return str(v)
