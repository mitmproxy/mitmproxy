import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--var', type=int)

var = 0


def start(ctx, argv):
    global var
    var = parser.parse_args(argv[1:]).var


def here(ctx):
    global var
    var += 1
    return var


def errargs():
    pass
