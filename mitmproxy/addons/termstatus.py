from mitmproxy import ctx
from mitmproxy.utils import human

"""
    A tiny addon to print the proxy status to terminal. Eventually this could
    also print some stats on exit.
"""


class TermStatus:
    def running(self):
        if ctx.options.server:
            ctx.log.info(
                "Proxy server listening at http://{}".format(
                    human.format_address(ctx.master.server.address)
                )
            )
