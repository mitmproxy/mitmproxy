# Usage: mitmdump -s "modify_response_body.py mitmproxy bananas"
# (this script works best with --anticache)
import sys

from mitmproxy.models import decoded
from mitmproxy import ctx

state = {}


def configure(options):
    if len(sys.argv) != 3:
        raise ValueError('Usage: -s "modify_response_body.py old new"')
    # You may want to use Python's argparse for more sophisticated argument
    # parsing.
    state["old"] = sys.argv[1]
    state["new"] = sys.argv[2]


def response():
    with decoded(ctx.flow.response):  # automatically decode gzipped responses.
        ctx.flow.response.content = ctx.flow.response.content.replace(
            state["old"],
            state["new"],
        )
