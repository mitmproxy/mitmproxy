import typing

from mitmproxy import exceptions
from mitmproxy import flow
from mitmproxy import ctx

from mitmproxy.tools.console import overlay
from mitmproxy.tools.console import signals


class CommandExecutor:
    def __init__(self, master):
        self.master = master

    def __call__(self, cmd):
        if cmd.strip():
            try:
                ret = self.master.commands.execute(cmd)
            except exceptions.CommandError as e:
                ctx.log.error(str(e))
            else:
                if ret:
                    if type(ret) == typing.Sequence[flow.Flow]:
                        signals.status_message.send(
                            message="Command returned %s flows" % len(ret)
                        )
                    elif type(ret) == flow.Flow:
                        signals.status_message.send(
                            message="Command returned 1 flow"
                        )
                    else:
                        self.master.overlay(
                            overlay.DataViewerOverlay(
                                self.master,
                                ret,
                            ),
                            valign="top"
                        )
