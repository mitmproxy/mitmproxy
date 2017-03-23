import argparse


class Replacer:
    def __init__(self, src, dst):
        self.src, self.dst = src, dst

    def response(self, flow):
        flow.response.replace(self.src, self.dst)


def load(opts):
    parser = argparse.ArgumentParser()
    parser.add_argument("src", type=str)
    parser.add_argument("dst", type=str)
    args = parser.parse_args()
    return Replacer(args.src, args.dst)
