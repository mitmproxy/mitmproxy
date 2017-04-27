import urwid

from mitmproxy import exceptions
from mitmproxy.tools.console import signals


class CommandEdit(urwid.Edit):
    def __init__(self, partial):
        urwid.Edit.__init__(self, ":", partial)

    def keypress(self, size, key):
        return urwid.Edit.keypress(self, size, key)


class CommandExecutor:
    def __init__(self, master):
        self.master = master

    def __call__(self, cmd):
        if cmd.strip():
            try:
                ret = self.master.commands.call(cmd)
            except exceptions.CommandError as v:
                signals.status_message.send(message=str(v))
            else:
                if type(ret) == str:
                    signals.status_message.send(message=ret)
