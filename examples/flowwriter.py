import random
import sys

from mitmproxy.flow import FlowWriter

state = {}


def start():
    if len(sys.argv) != 2:
        raise ValueError('Usage: -s "flowriter.py filename"')

    if sys.argv[1] == "-":
        f = sys.stdout
    else:
        f = open(sys.argv[1], "wb")
    state["flow_writer"] = FlowWriter(f)


def response(flow):
    if random.choice([True, False]):
        state["flow_writer"].add(flow)
