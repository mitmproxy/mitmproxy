import abc
import copy
import os
import typing
import urwid

from mitmproxy.utils import strutils
from mitmproxy import exceptions
from mitmproxy.tools.console import signals
from mitmproxy.tools.console import layoutwidget
import mitmproxy.tools.console.master # noqa


def read_file(filename: str, escaped: bool) -> typing.AnyStr:
    filename = os.path.expanduser(filename)
    try:
        with open(filename, "r" if escaped else "rb") as f:
            d = f.read()
    except IOError as v:
        raise exceptions.CommandError(v)
    if escaped:
        try:
            d = strutils.escaped_str_to_bytes(d)
        except ValueError:
            raise exceptions.CommandError("Invalid Python-style string encoding.")
    return d


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
    subeditor: urwid.Edit = None

    def __init__(self, heading):
        self.heading = heading

    @abc.abstractmethod
    def Display(self, data) -> Cell:
        pass

    @abc.abstractmethod
    def Edit(self, data) -> Cell:
        pass

    @abc.abstractmethod
    def blank(self) -> typing.Any:
        pass

    def keypress(self, key: str, editor: "GridEditor") -> typing.Optional[str]:
        return key


class GridRow(urwid.WidgetWrap):

    def __init__(
            self,
            focused: typing.Optional[int],
            editing: bool,
            editor: "GridEditor",
            values: typing.Tuple[typing.Iterable[bytes], typing.Container[int]]
    ) -> None:
        self.focused = focused
        self.editor = editor
        self.edit_col: typing.Optional[Cell] = None

        errors = values[1]
        self.fields: typing.Sequence[typing.Any] = []
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
            lst: typing.Iterable[list],
            editor: "GridEditor"
    ) -> None:
        self.lst: typing.Sequence[typing.Tuple[typing.Any, typing.Set]] = [(i, set()) for i in lst]
        self.editor = editor
        self.focus = 0
        self.focus_col = 0
        self.edit_row: typing.Optional[GridRow] = None

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
            self._modified()

    def stop_edit(self):
        if self.edit_row:
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


class BaseGridEditor(urwid.WidgetWrap):
    title: str = ""
    keyctx = "grideditor"

    def __init__(
            self,
            master: "mitmproxy.tools.console.master.ConsoleMaster",
            title,
            columns,
            value: typing.Any,
            callback: typing.Callable[..., None],
            *cb_args,
            **cb_kwargs
    ) -> None:
        value = self.data_in(copy.deepcopy(value))
        self.master = master
        self.title = title
        self.columns = columns
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

        h = None
        if any(col.heading for col in self.columns):
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
        w = urwid.Frame(self.lb, header=h)

        super().__init__(w)
        self.show_empty_msg()

    def layout_popping(self):
        res = []
        for i in self.walker.lst:
            if not i[1] and any([x for x in i[0]]):
                res.append(i[0])
        self.callback(self.data_out(res), *self.cb_args, **self.cb_kwargs)

    def show_empty_msg(self):
        if self.walker.lst:
            self._w.set_footer(None)
        else:
            self._w.set_footer(
                urwid.Text(
                    [
                        ("highlight", "No values - you should add some. Press "),
                        ("key", "?"),
                        ("highlight", " for help."),
                    ]
                )
            )

    def set_subeditor_value(self, val, focus, focus_col):
        self.walker.set_value(val, focus, focus_col)

    def keypress(self, size, key):
        if self.walker.edit_row:
            if key == "esc":
                self.walker.stop_edit()
            elif key == "tab":
                pf, pfc = self.walker.focus, self.walker.focus_col
                self.walker.tab_next()
                if self.walker.focus == pf and self.walker.focus_col != pfc:
                    self.walker.start_edit()
            else:
                self._w.keypress(size, key)
            return None

        column = self.columns[self.walker.focus_col]
        if key == "m_start":
            self.walker.set_focus(0)
        elif key == "m_next":
            self.walker.tab_next()
        elif key == "m_end":
            self.walker.set_focus(len(self.walker.lst) - 1)
        elif key == "left":
            self.walker.left()
        elif key == "right":
            self.walker.right()
        elif column.keypress(key, self) and not self.handle_key(key):
            return self._w.keypress(size, key)

    def data_out(self, data: typing.Sequence[list]) -> typing.Any:
        """
            Called on raw list data, before data is returned through the
            callback.
        """
        return data

    def data_in(self, data: typing.Any) -> typing.Iterable[list]:
        """
            Called to prepare provided data.
        """
        return data

    def is_error(self, col: int, val: typing.Any) -> typing.Optional[str]:
        """
            Return None, or a string error message.
        """
        return None

    def handle_key(self, key):
        return False

    def cmd_add(self):
        self.walker.add()

    def cmd_insert(self):
        self.walker.insert()

    def cmd_delete(self):
        self.walker.delete_focus()

    def cmd_read_file(self, path):
        self.walker.set_current_value(read_file(path, False))

    def cmd_read_file_escaped(self, path):
        self.walker.set_current_value(read_file(path, True))

    def cmd_spawn_editor(self):
        o = self.walker.get_current_value()
        if o is not None:
            n = self.master.spawn_editor(o)
            n = strutils.clean_hanging_newline(n)
            self.walker.set_current_value(n)


class GridEditor(BaseGridEditor):
    title = ""
    columns: typing.Sequence[Column] = ()
    keyctx = "grideditor"

    def __init__(
            self,
            master: "mitmproxy.tools.console.master.ConsoleMaster",
            value: typing.Any,
            callback: typing.Callable[..., None],
            *cb_args,
            **cb_kwargs
    ) -> None:
        super().__init__(
            master,
            self.title,
            self.columns,
            value,
            callback,
            *cb_args,
            **cb_kwargs
        )


class FocusEditor(urwid.WidgetWrap, layoutwidget.LayoutWidget):
    """
        A specialised GridEditor that edits the current focused flow.
    """
    keyctx = "grideditor"

    def __init__(self, master):
        self.master = master

    def call(self, v, name, *args, **kwargs):
        f = getattr(v, name, None)
        if f:
            f(*args, **kwargs)

    def get_data(self, flow):
        """
            Retrieve the data to edit from the current flow.
        """
        raise NotImplementedError

    def set_data(self, vals, flow):
        """
            Set the current data on the flow.
        """
        raise NotImplementedError

    def set_data_update(self, vals, flow):
        self.set_data(vals, flow)
        signals.flow_change.send(self, flow = flow)

    def key_responder(self):
        return self._w

    def layout_popping(self):
        self.call(self._w, "layout_popping")

    def layout_pushed(self, prev):
        if self.master.view.focus.flow:
            self._w = BaseGridEditor(
                self.master,
                self.title,
                self.columns,
                self.get_data(self.master.view.focus.flow),
                self.set_data_update,
                self.master.view.focus.flow,
            )
        else:
            self._w = urwid.Pile([])
