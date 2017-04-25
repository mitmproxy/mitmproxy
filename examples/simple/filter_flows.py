"""
This scripts demonstrates how to use mitmproxy's filter pattern in scripts.
Usage:
    mitmdump -s "flowfilter.py FILTER"
"""
import sys
from mitmproxy import flowfilter


class Filter:
    def __init__(self, spec):
        self.filter = flowfilter.parse(spec)

    def response(self, flow):
        if flowfilter.match(self.filter, flow):
            print("Flow matches filter:")
            print(flow)


addons = [Filter(sys.argv[1])]
