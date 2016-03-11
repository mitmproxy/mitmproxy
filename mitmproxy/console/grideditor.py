from __future__ import absolute_import

import copy
import re
import os
import urwid

from netlib import odict
from netlib.http import user_agents, cookies

from . import common, signals
from .. import utils, filt, script


FOOTER = [
    ('heading_key', "enter"), ":edit ",
    ('heading_key', "q"), ":back ",
]
FOOTER_EDITING = [
    ('heading_key', "esc"), ":stop editing ",
]


class TextColumn:
    subeditor = None

    def __init__(self, heading):
        self.heading = heading

    def text(self, obj):
        return SEscaped(obj or "")

    def blank(self):
        return ""

    def keypress(self, key, editor):
        if key == "r":
            if editor.walker.get_current_value() is not None:
                signals.status_prompt_path.send(
                    self,
                    prompt = "Read file",
                    callback = editor.read_file
                )
        elif key == "R":
            if editor.walker.get_current_value() is not None:
                signals.status_prompt_path.send(
                    editor,
                    prompt = "Read unescaped file",
                    callback = editor.read_file,
                    args = (True,)
                )
        elif key == "e":
            o = editor.walker.get_current_value()
            if o is not None:
                n = editor.master.spawn_editor(o.encode("string-escape"))
                n = utils.clean_hanging_newline(n)
                editor.walker.set_current_value(n, False)
                editor.walker._modified()
        elif key in ["enter"]:
            editor.walker.start_edit()
        else:
            return key


class SubgridColumn:

    def __init__(self, heading, subeditor):
        self.heading = heading
        self.subeditor = subeditor

    def text(self, obj):
        p = cookies._format_pairs(obj, sep="\n")
        return urwid.Text(p)

    def blank(self):
        return []

    def keypress(self, key, editor):
        if key in "rRe":
            signals.status_message.send(
                self,
                message = "Press enter to edit this field.",
                expire = 1000
            )
            return
        elif key in ["enter"]:
            editor.master.view_grideditor(
                self.subeditor(
                    editor.master,
                    editor.walker.get_current_value(),
                    editor.set_subeditor_value,
                    editor.walker.focus,
                    editor.walker.focus_col
                )
            )
        else:
            return key


class SEscaped(urwid.WidgetWrap):

    def __init__(self, txt):
        txt = txt.encode("string-escape")
        w = urwid.Text(txt, wrap="any")
        urwid.WidgetWrap.__init__(self, w)

    def get_text(self):
        return self._w.get_text()[0]

    def keypress(self, size, key):
        return key

    def selectable(self):
        return True


class SEdit(urwid.WidgetWrap):

    def __init__(self, txt):
        txt = txt.encode("string-escape")
        w = urwid.Edit(edit_text=txt, wrap="any", multiline=True)
        w = urwid.AttrWrap(w, "editfield")
        urwid.WidgetWrap.__init__(self, w)

    def get_text(self):
        return self._w.get_text()[0].strip()

    def selectable(self):
        return True


class GridRow(urwid.WidgetWrap):

    def __init__(self, focused, editing, editor, values):
        self.focused, self.editing, self.editor = focused, editing, editor

        errors = values[1]
        self.fields = []
        for i, v in enumerate(values[0]):
            if focused == i and editing:
                self.editing = SEdit(v)
                self.fields.append(self.editing)
            else:
                w = self.editor.columns[i].text(v)
                if focused == i:
                    if i in errors:
                        w = urwid.AttrWrap(w, "focusfield_error")
                    else:
                        w = urwid.AttrWrap(w, "focusfield")
                elif i in errors:
                    w = urwid.AttrWrap(w, "field_error")
                self.fields.append(w)

        fspecs = self.fields[:]
        if len(self.fields) > 1:
            fspecs[0] = ("fixed", self.editor.first_width + 2, fspecs[0])
        w = urwid.Columns(
            fspecs,
            dividechars = 2
        )
        if focused is not None:
            w.set_focus_column(focused)
        urwid.WidgetWrap.__init__(self, w)

    def get_edit_value(self):
        return self.editing.get_text()

    def keypress(self, s, k):
        if self.editing:
            w = self._w.column_widths(s)[self.focused]
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
                signals.status_message.send(
                    self,
                    message = "Invalid Python-style string encoding.",
                    expire = 1000
                )
                return
        errors = self.lst[self.focus][1]
        emsg = self.editor.is_error(self.focus_col, val)
        if emsg:
            signals.status_message.send(message = emsg, expire = 1)
            errors.add(self.focus_col)
        else:
            errors.discard(self.focus_col)
        self.set_value(val, self.focus, self.focus_col, errors)

    def set_value(self, val, focus, focus_col, errors=None):
        if not errors:
            errors = set([])
        row = list(self.lst[focus][0])
        row[focus_col] = val
        self.lst[focus] = [tuple(row), errors]
        self._modified()

    def delete_focus(self):
        if self.lst:
            del self.lst[self.focus]
            self.focus = min(len(self.lst) - 1, self.focus)
            self._modified()

    def _insert(self, pos):
        self.focus = pos
        self.lst.insert(
            self.focus,
            [
                [c.blank() for c in self.editor.columns], set([])
            ]
        )
        self.focus_col = 0
        self.start_edit()

    def insert(self):
        return self._insert(self.focus)

    def add(self):
        return self._insert(min(self.focus + 1, len(self.lst)))

    def start_edit(self):
        col = self.editor.columns[self.focus_col]
        if self.lst and not col.subeditor:
            self.editing = GridRow(
                self.focus_col, True, self.editor, self.lst[self.focus]
            )
            self.editor.master.loop.widget.footer.update(FOOTER_EDITING)
            self._modified()

    def stop_edit(self):
        if self.editing:
            self.editor.master.loop.widget.footer.update(FOOTER)
            self.set_current_value(self.editing.get_edit_value(), False)
            self.editing = False
            self._modified()

    def left(self):
        self.focus_col = max(self.focus_col - 1, 0)
        self._modified()

    def right(self):
        self.focus_col = min(self.focus_col + 1, len(self.editor.columns) - 1)
        self._modified()

    def tab_next(self):
        self.stop_edit()
        if self.focus_col < len(self.editor.columns) - 1:
            self.focus_col += 1
        elif self.focus != len(self.lst) - 1:
            self.focus_col = 0
            self.focus += 1
        self._modified()

    def get_focus(self):
        if self.editing:
            return self.editing, self.focus
        elif self.lst:
            return GridRow(
                self.focus_col,
                False,
                self.editor,
                self.lst[self.focus]
            ), self.focus
        else:
            return None, None

    def set_focus(self, focus):
        self.stop_edit()
        self.focus = focus
        self._modified()

    def get_next(self, pos):
        if pos + 1 >= len(self.lst):
            return None, None
        return GridRow(None, False, self.editor, self.lst[pos + 1]), pos + 1

    def get_prev(self, pos):
        if pos - 1 < 0:
            return None, None
        return GridRow(None, False, self.editor, self.lst[pos - 1]), pos - 1


class GridListBox(urwid.ListBox):

    def __init__(self, lw):
        urwid.ListBox.__init__(self, lw)


FIRST_WIDTH_MAX = 40
FIRST_WIDTH_MIN = 20


class GridEditor(urwid.WidgetWrap):
    title = None
    columns = None

    def __init__(self, master, value, callback, *cb_args, **cb_kwargs):
        value = self.data_in(copy.deepcopy(value))
        self.master, self.value, self.callback = master, value, callback
        self.cb_args, self.cb_kwargs = cb_args, cb_kwargs

        first_width = 20
        if value:
            for r in value:
                assert len(r) == len(self.columns)
                first_width = max(len(r), first_width)
        self.first_width = min(first_width, FIRST_WIDTH_MAX)

        title = urwid.Text(self.title)
        title = urwid.Padding(title, align="left", width=("relative", 100))
        title = urwid.AttrWrap(title, "heading")

        headings = []
        for i, col in enumerate(self.columns):
            c = urwid.Text(col.heading)
            if i == 0 and len(self.columns) > 1:
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
        self._w = urwid.Frame(
            self.lb,
            header = urwid.Pile([title, h])
        )
        self.master.loop.widget.footer.update("")
        self.show_empty_msg()

    def show_empty_msg(self):
        if self.walker.lst:
            self._w.set_footer(None)
        else:
            self._w.set_footer(
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
            except IOError as v:
                return str(v)

    def set_subeditor_value(self, val, focus, focus_col):
        self.walker.set_value(val, focus, focus_col)

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
                self._w.keypress(size, key)
            return None

        key = common.shortcuts(key)
        column = self.columns[self.walker.focus_col]
        if key in ["q", "esc"]:
            res = []
            for i in self.walker.lst:
                if not i[1] and any([x for x in i[0]]):
                    res.append(i[0])
            self.callback(self.data_out(res), *self.cb_args, **self.cb_kwargs)
            signals.pop_view_state.send(self)
        elif key == "g":
            self.walker.set_focus(0)
        elif key == "G":
            self.walker.set_focus(len(self.walker.lst) - 1)
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
        elif column.keypress(key, self) and not self.handle_key(key):
            return self._w.keypress(size, key)

    def data_out(self, data):
        """
            Called on raw list data, before data is returned through the
            callback.
        """
        return data

    def data_in(self, data):
        """
            Called to prepare provided data.
        """
        return data

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
            ("q", "save changes and exit editor"),
            ("r", "read value from file"),
            ("R", "read unescaped value from file"),
            ("esc", "save changes and exit editor"),
            ("tab", "next field"),
            ("enter", "edit field"),
        ]
        text.extend(
            common.format_keyvals(keys, key="key", val="text", indent=4)
        )
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
    columns = [
        TextColumn("Key"),
        TextColumn("Value")
    ]


class HeaderEditor(GridEditor):
    title = "Editing headers"
    columns = [
        TextColumn("Key"),
        TextColumn("Value")
    ]

    def make_help(self):
        h = GridEditor.make_help(self)
        text = []
        text.append(urwid.Text([("text", "Special keys:\n")]))
        keys = [
            ("U", "add User-Agent header"),
        ]
        text.extend(
            common.format_keyvals(keys, key="key", val="text", indent=4)
        )
        text.append(urwid.Text([("text", "\n")]))
        text.extend(h)
        return text

    def set_user_agent(self, k):
        ua = user_agents.get_by_shortcut(k)
        if ua:
            self.walker.add_value(
                [
                    "User-Agent",
                    ua[2]
                ]
            )

    def handle_key(self, key):
        if key == "U":
            signals.status_prompt_onekey.send(
                prompt = "Add User-Agent header:",
                keys = [(i[0], i[1]) for i in user_agents.UASTRINGS],
                callback = self.set_user_agent,
            )
            return True


class URLEncodedFormEditor(GridEditor):
    title = "Editing URL-encoded form"
    columns = [
        TextColumn("Key"),
        TextColumn("Value")
    ]


class ReplaceEditor(GridEditor):
    title = "Editing replacement patterns"
    columns = [
        TextColumn("Filter"),
        TextColumn("Regex"),
        TextColumn("Replacement"),
    ]

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
    columns = [
        TextColumn("Filter"),
        TextColumn("Header"),
        TextColumn("Value"),
    ]

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
        text.extend(
            common.format_keyvals(keys, key="key", val="text", indent=4)
        )
        text.append(urwid.Text([("text", "\n")]))
        text.extend(h)
        return text

    def set_user_agent(self, k):
        ua = user_agents.get_by_shortcut(k)
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
            signals.status_prompt_onekey.send(
                prompt = "Add User-Agent header:",
                keys = [(i[0], i[1]) for i in user_agents.UASTRINGS],
                callback = self.set_user_agent,
            )
            return True


class PathEditor(GridEditor):
    title = "Editing URL path components"
    columns = [
        TextColumn("Component"),
    ]

    def data_in(self, data):
        return [[i] for i in data]

    def data_out(self, data):
        return [i[0] for i in data]


class ScriptEditor(GridEditor):
    title = "Editing scripts"
    columns = [
        TextColumn("Command"),
    ]

    def is_error(self, col, val):
        try:
            script.Script.parse_command(val)
        except script.ScriptException as v:
            return str(v)


class HostPatternEditor(GridEditor):
    title = "Editing host patterns"
    columns = [
        TextColumn("Regex (matched on hostname:port / ip:port)")
    ]

    def is_error(self, col, val):
        try:
            re.compile(val, re.IGNORECASE)
        except re.error as e:
            return "Invalid regex: %s" % str(e)

    def data_in(self, data):
        return [[i] for i in data]

    def data_out(self, data):
        return [i[0] for i in data]


class CookieEditor(GridEditor):
    title = "Editing request Cookie header"
    columns = [
        TextColumn("Name"),
        TextColumn("Value"),
    ]


class CookieAttributeEditor(GridEditor):
    title = "Editing Set-Cookie attributes"
    columns = [
        TextColumn("Name"),
        TextColumn("Value"),
    ]

    def data_out(self, data):
        ret = []
        for i in data:
            if not i[1]:
                ret.append([i[0], None])
            else:
                ret.append(i)
        return ret


class SetCookieEditor(GridEditor):
    title = "Editing response SetCookie header"
    columns = [
        TextColumn("Name"),
        TextColumn("Value"),
        SubgridColumn("Attributes", CookieAttributeEditor),
    ]

    def data_in(self, data):
        flattened = []
        for k, v in data.items():
            flattened.append([k, v[0], v[1].lst])
        return flattened

    def data_out(self, data):
        vals = []
        for i in data:
            vals.append(
                [
                    i[0],
                    [i[1], odict.ODictCaseless(i[2])]
                ]
            )
        return odict.ODict(vals)
