import sys

from a_helper import parser

var = 0


def start(ctx):
    global var
    var = parser.parse_args(sys.argv[1:]).var


def here(ctx):
    global var
    var += 1
    return var


def errargs():
    pass
