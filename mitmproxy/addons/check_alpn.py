import mitmproxy
from mitmproxy.net import tcp


class CheckALPN:
    def __init__(self):
        self.failed = False

    def configure(self, options, updated):
        self.failed = mitmproxy.ctx.master.options.http2 and not tcp.HAS_ALPN
        if self.failed:
            mitmproxy.ctx.master.add_log(
                "HTTP/2 is disabled because ALPN support missing!\n"
                "OpenSSL 1.0.2+ required to support HTTP/2 connections.\n"
                "Use --no-http2 to silence this warning.",
                "warn",
            )
