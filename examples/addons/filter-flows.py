"""
Use mitmproxy's filter pattern in scripts.
"""
from mitmproxy import flowfilter
from mitmproxy import ctx, http


class Filter:
    def __init__(self):
        self.filter: flowfilter.TFilter = None

    def configure(self, updated):
        self.filter = flowfilter.parse(ctx.options.flowfilter)

    def load(self, l):
        l.add_option(
            "flowfilter", str, "", "Check that flow matches filter."
        )

    def response(self, flow: http.HTTPFlow) -> None:
        if flowfilter.match(self.filter, flow):
            ctx.log.info("Flow matches filter:")
            ctx.log.info(flow)


addons = [Filter()]
