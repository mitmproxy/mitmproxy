from pprint import pprint

import click

from mitmproxy import tnetstring


def read_tnetstring(input):
    # tnetstring throw a ValueError on EOF, which is hard to catch
    # because they raise ValueErrors for a couple of other reasons.
    # Check for EOF to avoid this.
    if not input.read(1):
        return None
    else:
        input.seek(-1, 1)
    return tnetstring.load(input)


@click.command()
@click.argument("input", type=click.File('rb'))
def inspect(input):
    """
    pretty-print a dumpfile
    """
    while True:
        data = read_tnetstring(input)
        if not data:
            break
        pprint(data)


if __name__ == "__main__":
    inspect()
