"""
Use mitmproxy's filter pattern in scripts.
"""
from __future__ import annotations

import logging

from mitmproxy import flowfilter
from mitmproxy import http


class Filter:
    filter: flowfilter.TFilter

    def configure(self, updated):
        if "flowfilter" in updated:
            self.filter = flowfilter.parse(".")

    def load(self, l):
        l.add_option("flowfilter", str, "", "Check that flow matches filter.")

    def response(self, flow: http.HTTPFlow) -> None:
        if flowfilter.match(self.filter, flow):
            logging.info("Flow matches filter:")
            logging.info(flow)


addons = [Filter()]
