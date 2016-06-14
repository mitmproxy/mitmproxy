# This scripts demonstrates how to use mitmproxy's filter pattern in inline scripts.
# Usage: mitmdump -s "filt.py FILTER"
import sys
from mitmproxy import filt


def start(context):
    if len(sys.argv) != 2:
        raise ValueError("Usage: -s 'filt.py FILTER'")
    context.filter = filt.parse(sys.argv[1])


def response(context, flow):
    if flow.match(context.filter):
        print("Flow matches filter:")
        print(flow)
