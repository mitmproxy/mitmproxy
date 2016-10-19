import abc
import copy
from typing import Any
from typing import Callable
from typing import Container
from typing import Iterable
from typing import Optional
from typing import Sequence
from typing import Tuple

import urwid
from mitmproxy.tools.console import common
from mitmproxy.tools.console import signals

FOOTER = [
    ('heading_key', "enter"), ":edit ",
    ('heading_key', "q"), ":back ",
]
FOOTER_EDITING = [
    ('heading_key', "esc"), ":stop editing ",
]


class Cell(urwid.WidgetWrap):
    def get_data(self):
        """
        Raises:
            ValueError, if the current content is invalid.
        """
        raise NotImplementedError()

    def selectable(self):
        return True


class Column(metaclass=abc.ABCMeta):
    subeditor = None

    def __init__(self, heading):
        self.heading = heading

    @abc.abstractmethod
    def Display(self, data) -> Cell:
        pass

    @abc.abstractmethod
    def Edit(self, data) -> Cell:
        pass

    @abc.abstractmethod
    def blank(self) -> Any:
        pass

    def keypress(self, key: str, editor: "GridEditor") -> Optional[str]:
        return key


class GridRow(urwid.WidgetWrap):
    def __init__(
            self,
            focused: Optional[int],
            editing: bool,
            editor: "GridEditor",
            values: Tuple[Iterable[bytes], Container[int]]
    ):
        self.focused = focused
        self.editor = editor
        self.edit_col = None  # type: Optional[Cell]

        errors = values[1]
        self.fields = []
        for i, v in enumerate(values[0]):
            if focused == i and editing:
                self.edit_col = self.editor.columns[i].Edit(v)
                self.fields.append(self.edit_col)
            else:
                w = self.editor.columns[i].Display(v)
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
            dividechars=2
        )
        if focused is not None:
            w.set_focus_column(focused)
        super().__init__(w)

    def keypress(self, s, k):
        if self.edit_col:
            w = self._w.column_widths(s)[self.focused]
            k = self.edit_col.keypress((w,), k)
        return k

    def selectable(self):
        return True


class GridWalker(urwid.ListWalker):
    """
        Stores rows as a list of (rows, errors) tuples, where rows is a list
        and errors is a set with an entry of each offset in rows that is an
        error.
    """

    def __init__(
            self,
            lst: Iterable[list],
            editor: "GridEditor"
    ):
        self.lst = [(i, set()) for i in lst]
        self.editor = editor
        self.focus = 0
        self.focus_col = 0
        self.edit_row = None  # type: Optional[GridRow]

    def _modified(self):
        self.editor.show_empty_msg()
        return super()._modified()

    def add_value(self, lst):
        self.lst.append(
            (lst[:], set())
        )
        self._modified()

    def get_current_value(self):
        if self.lst:
            return self.lst[self.focus][0][self.focus_col]

    def set_current_value(self, val):
        errors = self.lst[self.focus][1]
        emsg = self.editor.is_error(self.focus_col, val)
        if emsg:
            signals.status_message.send(message=emsg, expire=5)
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
            ([c.blank() for c in self.editor.columns], set([]))
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
            self.edit_row = GridRow(
                self.focus_col, True, self.editor, self.lst[self.focus]
            )
            self.editor.master.loop.widget.footer.update(FOOTER_EDITING)
            self._modified()

    def stop_edit(self):
        if self.edit_row:
            self.editor.master.loop.widget.footer.update(FOOTER)
            try:
                val = self.edit_row.edit_col.get_data()
            except ValueError:
                return
            self.edit_row = None
            self.set_current_value(val)

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
        if self.edit_row:
            return self.edit_row, self.focus
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
        super().__init__(lw)


FIRST_WIDTH_MAX = 40
FIRST_WIDTH_MIN = 20


class GridEditor(urwid.WidgetWrap):
    title = None  # type: str
    columns = None  # type: Sequence[Column]

    def __init__(
            self,
            master: "mitmproxy.console.master.ConsoleMaster",
            value: Any,
            callback: Callable[..., None],
            *cb_args,
            **cb_kwargs
    ):
        value = self.data_in(copy.deepcopy(value))
        self.master = master
        self.value = value
        self.callback = callback
        self.cb_args = cb_args
        self.cb_kwargs = cb_kwargs

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
            dividechars=2
        )
        h = urwid.AttrWrap(h, "heading")

        self.walker = GridWalker(self.value, self)
        self.lb = GridListBox(self.walker)
        w = urwid.Frame(
            self.lb,
            header=urwid.Pile([title, h])
        )
        super().__init__(w)
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

    def set_subeditor_value(self, val, focus, focus_col):
        self.walker.set_value(val, focus, focus_col)

    def keypress(self, size, key):
        if self.walker.edit_row:
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

    def data_out(self, data: Sequence[list]) -> Any:
        """
            Called on raw list data, before data is returned through the
            callback.
        """
        return data

    def data_in(self, data: Any) -> Iterable[list]:
        """
            Called to prepare provided data.
        """
        return data

    def is_error(self, col: int, val: Any) -> Optional[str]:
        """
            Return None, or a string error message.
        """
        return False

    def handle_key(self, key):
        return False

    def make_help(self):
        text = [
            urwid.Text([("text", "Editor control:\n")])
        ]
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
