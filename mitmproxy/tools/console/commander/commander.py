import urwid
from urwid.text_layout import calc_coords


class CommandBuffer():
    def __init__(self, start: str = "") -> None:
        self.buf = start
        # This is the logical cursor position - the display cursor is one
        # character further on. Cursor is always within the range [0:len(buffer)].
        self._cursor = len(self.buf)

    @property
    def cursor(self) -> int:
        return self._cursor

    @cursor.setter
    def cursor(self, x) -> None:
        if x < 0:
            self._cursor = 0
        elif x > len(self.buf):
            self._cursor = len(self.buf)
        else:
            self._cursor = x

    def render(self):
        return self.buf

    def left(self) -> None:
        self.cursor = self.cursor - 1

    def right(self) -> None:
        self.cursor = self.cursor + 1

    def backspace(self) -> None:
        if self.cursor == 0:
            return
        self.buf = self.buf[:self.cursor - 1] + self.buf[self.cursor:]
        self.cursor = self.cursor - 1

    def insert(self, k: str) -> None:
        """
            Inserts text at the cursor.
        """
        self.buf = self.buf = self.buf[:self.cursor] + k + self.buf[self.cursor:]
        self.cursor += 1


class CommandEdit(urwid.WidgetWrap):
    leader = ": "

    def __init__(self, text) -> None:
        self.cbuf = CommandBuffer(text)
        self._w = urwid.Text(self.leader)
        self.update()

    def keypress(self, size, key):
        if key == "backspace":
            self.cbuf.backspace()
        elif key == "left":
            self.cbuf.left()
        elif key == "right":
            self.cbuf.right()
        elif len(key) == 1:
            self.cbuf.insert(key)
        self.update()

    def update(self):
        self._w.set_text([self.leader, self.cbuf.render()])

    def render(self, size, focus=False):
        (maxcol,) = size
        canv = self._w.render((maxcol,))
        canv = urwid.CompositeCanvas(canv)
        canv.cursor = self.get_cursor_coords((maxcol,))
        return canv

    def get_cursor_coords(self, size):
        p = self.cbuf.cursor + len(self.leader)
        trans = self._w.get_line_translation(size[0])
        x, y = calc_coords(self._w.get_text()[0], trans, p)
        return x, y

    def get_value(self):
        return self.cbuf.buf
