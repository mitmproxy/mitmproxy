import abc
import glob
import os
import typing

import urwid
from urwid.text_layout import calc_coords

import mitmproxy.master
import mitmproxy.command


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


# Generates the completion options for a specific starting input
def pathOptions(start: str) -> typing.Sequence[str]:
    if not start:
        start = "./"
    path = os.path.expanduser(start)
    ret = []
    if os.path.isdir(path):
        files = glob.glob(os.path.join(path, "*"))
        prefix = start
    else:
        files = glob.glob(path + "*")
        prefix = os.path.dirname(start)
    prefix = prefix or "./"
    for f in files:
        display = os.path.join(prefix, os.path.normpath(os.path.basename(f)))
        if os.path.isdir(f):
            display += "/"
        ret.append(display)
    if not ret:
        ret = [start]
    ret.sort()
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
        self.buf = start
        # Cursor is always within the range [0:len(buffer)].
        self._cursor = len(self.buf)
        self.completion = None   # type: CompletionState

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

    def cycle_completion(self) -> None:
        if not self.completion:
            parts = self.master.commands.parse_partial(self.buf[:self.cursor])
            last = parts[-1]
            if last.type == mitmproxy.command.Cmd:
                self.completion = CompletionState(
                    completer = ListCompleter(
                        parts[-1].value,
                        self.master.commands.commands.keys(),
                    ),
                    parse = parts,
                )
            if last.type == typing.Sequence[mitmproxy.command.Cut]:
                spec = parts[-1].value.split(",")
                opts = []
                for pref in mitmproxy.command.Cut.valid_prefixes:
                    spec[-1] = pref
                    opts.append(",".join(spec))
                self.completion = CompletionState(
                    completer = ListCompleter(
                        parts[-1].value,
                        opts,
                    ),
                    parse = parts,
                )
            elif isinstance(last.type, mitmproxy.command.Choice):
                self.completion = CompletionState(
                    completer = ListCompleter(
                        parts[-1].value,
                        self.master.commands.call(last.type.options_command),
                    ),
                    parse = parts,
                )
            elif last.type == mitmproxy.command.Path:
                self.completion = CompletionState(
                    completer = ListCompleter(
                        "",
                        pathOptions(parts[1].value)
                    ),
                    parse = parts,
                )

        if self.completion:
            nxt = self.completion.completer.cycle()
            buf = " ".join([i.value for i in self.completion.parse[:-1]]) + " " + nxt
            buf = buf.strip()
            self.buf = buf
            self.cursor = len(self.buf)

    def backspace(self) -> None:
        if self.cursor == 0:
            return
        self.buf = self.buf[:self.cursor - 1] + self.buf[self.cursor:]
        self.cursor = self.cursor - 1
        self.completion = None

    def insert(self, k: str) -> None:
        """
            Inserts text at the cursor.
        """
        self.buf = self.buf = self.buf[:self.cursor] + k + self.buf[self.cursor:]
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
        return self.cbuf.buf
