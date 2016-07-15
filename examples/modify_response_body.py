# Usage: mitmdump -s "modify_response_body.py mitmproxy bananas"
# (this script works best with --anticache)
import sys

from mitmproxy.models import decoded


state = {}


def start():
    if len(sys.argv) != 3:
        raise ValueError('Usage: -s "modify_response_body.py old new"')
    # You may want to use Python's argparse for more sophisticated argument
    # parsing.
    state["old"], state["new"] = sys.argv[1].encode(), sys.argv[2].encode()


def response(flow):
    with decoded(flow.response):  # automatically decode gzipped responses.
        flow.response.content = flow.response.content.replace(
            state["old"],
            state["new"]
        )
