from __future__ import absolute_import, print_function, division

from mitmproxy import ctx
from mitmproxy import filt
from mitmproxy import exceptions


class StickyAuth:
    def __init__(self):
        # Compiled filter
        self.flt = None
        self.hosts = {}

    def configure(self, options):
        if options.stickyauth:
            flt = filt.parse(options.stickyauth)
            if not flt:
                raise exceptions.OptionsError(
                    "stickyauth: invalid filter expression: %s" % options.stickyauth
                )
            self.flt = flt

    def request(self):
        host = ctx.flow.request.host
        if "authorization" in ctx.flow.request.headers:
            self.hosts[host] = ctx.flow.request.headers["authorization"]
        elif ctx.flow.match(self.flt):
            if host in self.hosts:
                ctx.flow.request.headers["authorization"] = self.hosts[host]
