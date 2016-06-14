import random
import sys

from mitmproxy.flow import FlowWriter


def start(context):
    if len(sys.argv) != 2:
        raise ValueError('Usage: -s "flowriter.py filename"')

    if sys.argv[1] == "-":
        f = sys.stdout
    else:
        f = open(sys.argv[1], "wb")
    context.flow_writer = FlowWriter(f)


def response(context, flow):
    if random.choice([True, False]):
        context.flow_writer.add(flow)
