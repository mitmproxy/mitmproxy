"""
This scripts demonstrates how to use mitmproxy's filter pattern in scripts.
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
            print("Flow matches filter:")
            print(flow)


addons = [Filter()]
