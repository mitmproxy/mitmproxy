import random
import sys
from mimtproxy import io


class Writer:
    def __init__(self, path):
        if path == "-":
            f = sys.stdout
        else:
            f = open(path, "wb")
        self.w = io.FlowWriter(f)

    def response(self, flow):
        if random.choice([True, False]):
            self.w.add(flow)


def start():
    if len(sys.argv) != 2:
        raise ValueError('Usage: -s "flowriter.py filename"')
    return Writer(sys.argv[1])
