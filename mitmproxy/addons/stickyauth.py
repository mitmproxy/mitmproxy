from mitmproxy import exceptions
from mitmproxy import flowfilter


class StickyAuth:
    def __init__(self):
        self.flt = None
        self.hosts = {}

    def configure(self, options, updated):
        if "stickyauth" in updated:
            if options.stickyauth:
                flt = flowfilter.parse(options.stickyauth)
                if not flt:
                    raise exceptions.OptionsError(
                        "stickyauth: invalid filter expression: %s" % options.stickyauth
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
