import random
import sys

from mitmproxy.flow import FlowWriter


def start(context, argv):
    if len(argv) != 2:
        raise ValueError('Usage: -s "flowriter.py filename"')

    if argv[1] == "-":
        f = sys.stdout
    else:
        f = open(argv[1], "wb")
    context.flow_writer = FlowWriter(f)


def response(context, flow):
    if random.choice([True, False]):
        context.flow_writer.add(flow)
