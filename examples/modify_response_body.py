# Usage: mitmdump -s "modify_response_body.py mitmproxy bananas"
# (this script works best with --anticache)
from libmproxy.protocol.http import decoded


def start(context, argv):
    if len(argv) != 3:
        raise ValueError('Usage: -s "modify-response-body.py old new"')
    # You may want to use Python's argparse for more sophisticated argument parsing.
    context.old, context.new = argv[1], argv[2]


def response(context, flow):
    with decoded(flow.response):  # automatically decode gzipped responses.
        flow.response.content = flow.response.content.replace(context.old, context.new)