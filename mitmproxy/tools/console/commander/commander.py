import abc
import typing

import urwid
from urwid.text_layout import calc_coords

import mitmproxy.flow
import mitmproxy.master
import mitmproxy.command
import mitmproxy.types


class Completer:  # pragma: no cover
    @abc.abstractmethod
    def cycle(self) -> str:
        pass


class ListCompleter(Completer):
    def __init__(
        self,
        start: str,
        options: typing.Sequence[str],
    ) -> None:
        self.start = start
        self.options = []  # type: typing.Sequence[str]
        for o in options:
            if o.startswith(start):
                self.options.append(o)
        self.options.sort()
        self.offset = 0

    def cycle(self) -> str:
        if not self.options:
            return self.start
        ret = self.options[self.offset]
        self.offset = (self.offset + 1) % len(self.options)
        return ret


CompletionState = typing.NamedTuple(
    "CompletionState",
    [
        ("completer", Completer),
        ("parse", typing.Sequence[mitmproxy.command.ParseResult])
    ]
)


class CommandBuffer():
    def __init__(self, master: mitmproxy.master.Master, start: str = "") -> None:
        self.master = master
        self.text = self.flatten(start)
        # Cursor is always within the range [0:len(buffer)].
        self._cursor = len(self.text)
        self.completion = None   # type: CompletionState

    @property
    def cursor(self) -> int:
        return self._cursor

    @cursor.setter
    def cursor(self, x) -> None:
        if x < 0:
            self._cursor = 0
        elif x > len(self.text):
            self._cursor = len(self.text)
        else:
            self._cursor = x

    def render(self):
        parts, _ = self.master.commands.parse_partial(self.text)
        ret = []
        for p in parts:
            if p.type == mitmproxy.types.Cmd and p.valid:
                ret.append(("title", p.value))
            else:
                ret.append(("text", p.value))
            ret.append(("text", " "))
        return ret

    def flatten(self, txt):
        parts, _ = self.master.commands.parse_partial(txt)
        return " ".join([x.value for x in parts])

    def left(self) -> None:
        self.cursor = self.cursor - 1

    def right(self) -> None:
        self.cursor = self.cursor + 1

    def cycle_completion(self) -> None:
        if not self.completion:
            parts, remainhelp = self.master.commands.parse_partial(self.text[:self.cursor])
            last = parts[-1]
            ct = mitmproxy.types.CommandTypes.get(last.type, None)
            if ct:
                self.completion = CompletionState(
                    completer = ListCompleter(
                        parts[-1].value,
                        ct.completion(self.master.commands, last.type, parts[-1].value)
                    ),
                    parse = parts,
                )
        if self.completion:
            nxt = self.completion.completer.cycle()
            buf = " ".join([i.value for i in self.completion.parse[:-1]]) + " " + nxt
            buf = buf.strip()
            self.text = self.flatten(buf)
            self.cursor = len(self.text)

    def backspace(self) -> None:
        if self.cursor == 0:
            return
        self.text = self.flatten(self.text[:self.cursor - 1] + self.text[self.cursor:])
        self.cursor = self.cursor - 1
        self.completion = None

    def insert(self, k: str) -> None:
        """
            Inserts text at the cursor.
        """
        self.text = self.flatten(self.text[:self.cursor] + k + self.text[self.cursor:])
        self.cursor += 1
        self.completion = None


class CommandEdit(urwid.WidgetWrap):
    leader = ": "

    def __init__(self, master: mitmproxy.master.Master, text: str) -> None:
        super().__init__(urwid.Text(self.leader))
        self.master = master
        self.cbuf = CommandBuffer(master, text)
        self.update()

    def keypress(self, size, key):
        if key == "backspace":
            self.cbuf.backspace()
        elif key == "left":
            self.cbuf.left()
        elif key == "right":
            self.cbuf.right()
        elif key == "tab":
            self.cbuf.cycle_completion()
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
        return self.cbuf.text
