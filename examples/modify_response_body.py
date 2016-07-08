# Usage: mitmdump -s "modify_response_body.py mitmproxy bananas"
# (this script works best with --anticache)
import sys

from mitmproxy.models import decoded


def start(context):
    if len(sys.argv) != 3:
        raise ValueError('Usage: -s "modify_response_body.py old new"')
    # You may want to use Python's argparse for more sophisticated argument
    # parsing.
    context.old, context.new = sys.argv[1].encode(), sys.argv[2].encode()


def response(context, flow):
    with decoded(flow.response):  # automatically decode gzipped responses.
        flow.response.content = flow.response.content.replace(
            context.old,
            context.new)
