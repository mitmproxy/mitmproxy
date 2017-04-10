from mitmproxy import ctx
from mitmproxy.utils import human

"""
    A tiny addon to print the proxy status to terminal. Eventually this could
    also print some stats on exit.
"""


class TermStatus:
    def __init__(self):
        self.server = False

    def configure(self, options, updated):
        if "server" in updated:
            self.server = options.server

    def running(self):
        if self.server:
            ctx.log.info(
                "Proxy server listening at http://{}".format(
                    human.format_address(ctx.master.server.address)
                )
            )
