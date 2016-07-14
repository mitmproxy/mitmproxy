# This scripts demonstrates how to use mitmproxy's filter pattern in inline scripts.
# Usage: mitmdump -s "filt.py FILTER"
import sys
from mitmproxy import filt

state = {}


def configure(options):
    if len(sys.argv) != 2:
        raise ValueError("Usage: -s 'filt.py FILTER'")
    state["filter"] = filt.parse(sys.argv[1])


def response(flow):
    if flow.match(state["filter"]):
        print("Flow matches filter:")
        print(flow)
