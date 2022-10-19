"""
Use mitmproxy's filter pattern in scripts.
"""
import logging

from mitmproxy import ctx, http
from mitmproxy import flowfilter


class Filter:
    def __init__(self):
        self.filter: flowfilter.TFilter = None

    def configure(self, updated):
        if "flowfilter" in updated:
            self.filter = flowfilter.parse(ctx.options.flowfilter)

    def load(self, l):
        l.add_option("flowfilter", str, "", "Check that flow matches filter.")

    def response(self, flow: http.HTTPFlow) -> None:
        if flowfilter.match(self.filter, flow):
            logging.info("Flow matches filter:")
            logging.info(flow)


addons = [Filter()]
