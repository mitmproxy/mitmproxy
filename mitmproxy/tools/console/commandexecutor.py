import typing
import asyncio

from mitmproxy import exceptions
from mitmproxy import flow

from mitmproxy.tools.console import overlay
from mitmproxy.tools.console import signals


class CommandExecutor:
    def __init__(self, master):
        self.master = master

    def __call__(self, cmd):
        if cmd.strip():
            try:
                ret = self.master.commands.execute(cmd)
            except exceptions.ExecutionError:
                # Asynchronous launch
                command_task = self.master.commands.async_execute(cmd)
                command_task.add_done_callback(self.check_return)
            except exceptions.CommandError as v:
                signals.status_message.send(message=str(v))
            else:
                self.check_return(ret=ret)

    def check_return(self, task=None, ret=None):
        if task is not None:
            try:
                ret = task.result()
            except asyncio.CancelledError:
                return
        if ret:
            if type(ret) == typing.Sequence[flow.Flow]:
                signals.status_message.send(
                    message=f"Command returned {len(ret)} flows"
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
