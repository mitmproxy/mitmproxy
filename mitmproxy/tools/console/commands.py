import textwrap

import urwid

from mitmproxy import command
from mitmproxy.tools.console import layoutwidget
from mitmproxy.tools.console import signals
from mitmproxy.utils import signals as utils_signals

HELP_HEIGHT = 5

command_focus_change = utils_signals.SyncSignal(lambda text: None)


class CommandItem(urwid.WidgetWrap):
    def __init__(self, walker, cmd: command.Command, focused: bool):
        self.walker, self.cmd, self.focused = walker, cmd, focused
        super().__init__(self.get_widget())

    def get_widget(self):
        parts = [("focus", ">> " if self.focused else "   "), ("title", self.cmd.name)]
        if self.cmd.parameters:
            parts += [
                ("text", " "),
                ("text", " ".join(str(param) for param in self.cmd.parameters)),
            ]
        if self.cmd.return_type:
            parts += [
                ("title", " -> "),
                ("text", command.typename(self.cmd.return_type)),
            ]

        return urwid.AttrMap(urwid.Padding(urwid.Text(parts)), "text")

    def get_edit_text(self):
        return self._w[1].get_edit_text()

    def selectable(self):
        return True

    def keypress(self, size, key):
        return key


class CommandListWalker(urwid.ListWalker):
    def __init__(self, master):
        self.master = master
        self.index = 0
        self.refresh()

    def refresh(self):
        self.cmds = list(self.master.commands.commands.values())
        self.cmds.sort(key=lambda x: x.signature_help())
        self.set_focus(self.index)

    def get_edit_text(self):
        return self.focus_obj.get_edit_text()

    def _get(self, pos):
        cmd = self.cmds[pos]
        return CommandItem(self, cmd, pos == self.index)

    def get_focus(self):
        return self.focus_obj, self.index

    def set_focus(self, index: int) -> None:
        cmd = self.cmds[index]
        self.index = index
        self.focus_obj = self._get(self.index)
        command_focus_change.send(cmd.help or "")

    def get_next(self, pos):
        if pos >= len(self.cmds) - 1:
            return None, None
        pos = pos + 1
        return self._get(pos), pos

    def get_prev(self, pos):
        pos = pos - 1
        if pos < 0:
            return None, None
        return self._get(pos), pos


class CommandsList(urwid.ListBox):
    def __init__(self, master):
        self.master = master
        self.walker = CommandListWalker(master)
        super().__init__(self.walker)

    def keypress(self, size: int, key: str):
        if key == "m_select":
            foc, idx = self.get_focus()
            signals.status_prompt_command.send(partial=foc.cmd.name + " ")
        elif key == "m_start":
            self.set_focus(0)
            self.walker._modified()
        elif key == "m_end":
            self.set_focus(len(self.walker.cmds) - 1)
            self.walker._modified()
        return super().keypress(size, key)


class CommandHelp(urwid.Frame):
    def __init__(self, master):
        self.master = master
        super().__init__(self.widget(""))
        self.set_active(False)
        command_focus_change.connect(self.sig_mod)

    def set_active(self, val):
        h = urwid.Text("Command Help")
        style = "heading" if val else "heading_inactive"
        self.header = urwid.AttrMap(h, style)

    def widget(self, txt):
        cols, _ = self.master.ui.get_cols_rows()
        return urwid.ListBox([urwid.Text(i) for i in textwrap.wrap(txt, cols)])

    def sig_mod(self, txt):
        self.body = self.widget(txt)


class Commands(urwid.Pile, layoutwidget.LayoutWidget):
    title = "Command Reference"
    keyctx = "commands"

    focus_position: int

    def __init__(self, master):
        oh = CommandHelp(master)
        super().__init__(
            [
                CommandsList(master),
                (HELP_HEIGHT, oh),
            ]
        )
        self.master = master

    def layout_pushed(self, prev):
        self.widget_list[0].walker.refresh()

    def keypress(self, size, key):
        if key == "m_next":
            self.focus_position = (self.focus_position + 1) % len(self.widget_list)
            self.widget_list[1].set_active(self.focus_position == 1)
            key = None

        # This is essentially a copypasta from urwid.Pile's keypress handler.
        # So much for "closed for modification, but open for extension".
        item_rows = None
        if len(size) == 2:
            item_rows = self.get_item_rows(size, focus=True)
        i = self.widget_list.index(self.focus_item)
        tsize = self.get_item_size(size, i, True, item_rows)
        return self.focus_item.keypress(tsize, key)
