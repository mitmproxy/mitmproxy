# Usage: mitmdump -s "modify_response_body.py mitmproxy bananas"
# (this script works best with --anticache)
import sys


def start(context):
    if len(sys.argv) != 3:
        raise ValueError('Usage: -s "modify_response_body.py old new"')
    # You may want to use Python's argparse for more sophisticated argument
    # parsing.
    context.old, context.new = sys.argv[1], sys.argv[2]


def response(context, flow):
    flow.response.content = flow.response.content.replace(
        context.old,
        context.new
    )
