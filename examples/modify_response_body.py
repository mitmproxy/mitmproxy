# Usage: mitmdump -s "modify_response_body.py mitmproxy bananas"
# (works best with --anticache)

import sys
from libmproxy.protocol.http import decoded


def start(ctx, argv):
    if len(argv) != 3:
        sys.exit('Usage: -s "modify-response-body.py old new"')
    global old, new  # In larger scripts, a centralized options object (as returned by argparse) is encouraged
    old, new = argv[1:]


def response(ctx, flow):
    with decoded(flow.response):  # automatically decode gzipped responses.
        flow.response.content = flow.response.content.replace(old, new)