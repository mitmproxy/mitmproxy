import logging
from collections.abc import Sequence

from mitmproxy import exceptions
from mitmproxy import flow
from mitmproxy.tools.console import overlay
from mitmproxy.tools.console import signals


class CommandExecutor:
    def __init__(self, master):
        self.master = master

    def __call__(self, cmd: str) -> None:
        if cmd.strip():
            try:
                ret = self.master.commands.execute(cmd)
            except exceptions.CommandError as e:
                logging.error(str(e))
            else:
                if ret is not None:
                    if type(ret) == Sequence[flow.Flow]:  # noqa: E721
                        signals.status_message.send(
                            message="Command returned %s flows" % len(ret)
                        )
                    elif type(ret) is flow.Flow:
                        signals.status_message.send(message="Command returned 1 flow")
                    else:
                        self.master.overlay(
                            overlay.DataViewerOverlay(
                                self.master,
                                ret,
                            ),
                            valign="top",
                        )
