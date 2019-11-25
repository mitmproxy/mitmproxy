import abc
import typing

import urwid
from urwid.text_layout import calc_coords

import mitmproxy.command
import mitmproxy.flow
import mitmproxy.master
import mitmproxy.types

from mitmproxy import command_lexer


class Completer:
    @abc.abstractmethod
    def cycle(self, forward: bool = True) -> str:
        raise NotImplementedError()


class ListCompleter(Completer):
    def __init__(
            self,
            start: str,
            options: typing.Sequence[str],
    ) -> None:
        self.start = start
        self.options: typing.List[str] = []
        for o in options:
            if o.startswith(start):
                self.options.append(o)
        self.options.sort()
        self.offset = 0

    def cycle(self, forward: bool = True) -> str:
        if not self.options:
            return self.start
        ret = self.options[self.offset]
        delta = 1 if forward else -1
        self.offset = (self.offset + delta) % len(self.options)
        return ret


class CompletionState(typing.NamedTuple):
    completer: Completer
    parsed: typing.Sequence[mitmproxy.command.ParseResult]


class CommandBuffer:
    def __init__(self, master: mitmproxy.master.Master, start: str = "") -> None:
        self.master = master
        self.text = start
        # Cursor is always within the range [0:len(buffer)].
        self._cursor = len(self.text)
        self.completion: typing.Optional[CompletionState] = None

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
        parts, remaining = self.master.commands.parse_partial(self.text)
        ret = []
        if not parts:
            # Means we just received the leader, so we need to give a blank
            # text to the widget to render or it crashes
            ret.append(("text", ""))
        else:
            for p in parts:
                if p.valid:
                    if p.type == mitmproxy.types.Cmd:
                        ret.append(("commander_command", p.value))
                    else:
                        ret.append(("text", p.value))
                elif p.value:
                    ret.append(("commander_invalid", p.value))

            if remaining:
                if parts[-1].type != mitmproxy.types.Space:
                    ret.append(("text", " "))
                for param in remaining:
                    ret.append(("commander_hint", f"{param} "))

        return ret

    def left(self) -> None:
        self.cursor = self.cursor - 1

    def right(self) -> None:
        self.cursor = self.cursor + 1

    def cycle_completion(self, forward: bool = True) -> None:
        if not self.completion:
            parts, remaining = self.master.commands.parse_partial(self.text[:self.cursor])
            if parts and parts[-1].type != mitmproxy.types.Space:
                type_to_complete = parts[-1].type
                cycle_prefix = parts[-1].value
                parsed = parts[:-1]
            elif remaining:
                type_to_complete = remaining[0].type
                cycle_prefix = ""
                parsed = parts
            else:
                return
            ct = mitmproxy.types.CommandTypes.get(type_to_complete, None)
            if ct:
                self.completion = CompletionState(
                    completer=ListCompleter(
                        cycle_prefix,
                        ct.completion(self.master.commands, type_to_complete, cycle_prefix)
                    ),
                    parsed=parsed,
                )
        if self.completion:
            nxt = self.completion.completer.cycle(forward)
            buf = "".join([i.value for i in self.completion.parsed]) + nxt
            self.text = buf
            self.cursor = len(self.text)

    def backspace(self) -> None:
        if self.cursor == 0:
            return
        self.text = self.text[:self.cursor - 1] + self.text[self.cursor:]
        self.cursor = self.cursor - 1
        self.completion = None

    def insert(self, k: str) -> None:
        """
            Inserts text at the cursor.
        """

        # We don't want to insert a space before the command
        if k == ' ' and self.text[0:self.cursor].strip() == '':
            return

        self.text = self.text[:self.cursor] + k + self.text[self.cursor:]
        self.cursor += len(k)
        self.completion = None


class CommandEdit(urwid.WidgetWrap):
    leader = ": "

    def __init__(self, master: mitmproxy.master.Master, text: str) -> None:
        super().__init__(urwid.Text(self.leader))
        self.master = master
        self.active_filter = False
        self.filter_str = ''
        self.cbuf = CommandBuffer(master, text)
        self.update()

    def keypress(self, size, key) -> None:
        if key == "backspace":
            self.cbuf.backspace()
            if self.cbuf.text == '':
                self.active_filter = False
                self.master.commands.execute("command_history.filter ''")
                self.filter_str = ''
        elif key == "left":
            self.cbuf.left()
        elif key == "right":
            self.cbuf.right()
        elif key == "up":
            if self.active_filter is False:
                self.active_filter = True
                self.filter_str = self.cbuf.text
                _cmd = command_lexer.quote(self.cbuf.text)
                self.master.commands.execute("command_history.filter %s" % _cmd)

            cmd = self.master.commands.execute("command_history.prev")
            self.cbuf = CommandBuffer(self.master, cmd)
        elif key == "down":
            prev_cmd = self.cbuf.text
            cmd = self.master.commands.execute("command_history.next")

            if cmd == '':
                if prev_cmd == self.filter_str:
                    self.cbuf = CommandBuffer(self.master, prev_cmd)
                else:
                    self.active_filter = False
                    self.master.commands.execute("command_history.filter ''")
                    self.filter_str = ''
                    self.cbuf = CommandBuffer(self.master, '')
            else:
                self.cbuf = CommandBuffer(self.master, cmd)

        elif key == "shift tab":
            self.cbuf.cycle_completion(False)
        elif key == "tab":
            self.cbuf.cycle_completion()
        elif len(key) == 1:
            self.cbuf.insert(key)
        self.update()

    def update(self) -> None:
        self._w.set_text([self.leader, self.cbuf.render()])

    def render(self, size, focus=False) -> urwid.Canvas:
        (maxcol,) = size
        canv = self._w.render((maxcol,))
        canv = urwid.CompositeCanvas(canv)
        canv.cursor = self.get_cursor_coords((maxcol,))
        return canv

    def get_cursor_coords(self, size) -> typing.Tuple[int, int]:
        p = self.cbuf.cursor + len(self.leader)
        trans = self._w.get_line_translation(size[0])
        x, y = calc_coords(self._w.get_text()[0], trans, p)
        return x, y

    def get_edit_text(self) -> str:
        return self.cbuf.text
