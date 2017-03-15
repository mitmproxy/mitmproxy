from mitmproxy import ctx

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
                "Proxy server listening at http://{}:{}".format(
                    *ctx.master.server.address,
                )
            )
