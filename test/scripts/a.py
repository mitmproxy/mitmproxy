import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--var')

var = 0
def __init__(ctx, argv):
    global var
    var = parser.parse_args(argv).var

def here(ctx):
    global var
    var += 1
    return var

def errargs():
    pass
