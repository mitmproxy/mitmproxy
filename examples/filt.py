# This scripts demonstrates how to use mitmproxy's filter pattern in scripts.
# Usage: mitmdump -s "filt.py FILTER"
import sys
from mitmproxy import filt


class Filter:
    def __init__(self, spec):
        self.filter = filt.parse(spec)

    def response(self, flow):
        if flow.match(self.filter):
            print("Flow matches filter:")
            print(flow)


def start():
    if len(sys.argv) != 2:
        raise ValueError("Usage: -s 'filt.py FILTER'")
    return Filter(sys.argv[1])
