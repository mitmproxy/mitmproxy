import urwid

from mitmproxy import command
from mitmproxy.tools.console import signals


class CommandEdit(urwid.Edit):
    def __init__(self):
        urwid.Edit.__init__(self, ":", "")

    def keypress(self, size, key):
        return urwid.Edit.keypress(self, size, key)


class CommandExecutor:
    def __init__(self, master):
        self.master = master

    def __call__(self, cmd):
        try:
            ret = self.master.commands.call(cmd)
        except command.CommandError as v:
            signals.status_message.send(message=str(v))
        else:
            if type(ret) == str:
                signals.status_message.send(message=ret)
