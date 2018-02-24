import typing

from mitmproxy import exceptions
from mitmproxy import flowfilter
from mitmproxy import ctx


class StickyAuth:
    def __init__(self):
        self.flt = None
        self.hosts = {}

    def load(self, loader):
        loader.add_option(
            "stickyauth", typing.Optional[str], None,
            "Set sticky auth filter. Matched against requests."
        )

    def configure(self, updated):
        if "stickyauth" in updated:
            if ctx.options.stickyauth:
                flt = flowfilter.parse(ctx.options.stickyauth)
                if not flt:
                    raise exceptions.OptionsError(
                        "stickyauth: invalid filter expression: %s" % ctx.options.stickyauth
                    )
                self.flt = flt
            else:
                self.flt = None

    def request(self, flow):
        if self.flt:
            host = flow.request.host
            if "authorization" in flow.request.headers:
                self.hosts[host] = flow.request.headers["authorization"]
            elif flowfilter.match(self.flt, flow):
                if host in self.hosts:
                    flow.request.headers["authorization"] = self.hosts[host]
