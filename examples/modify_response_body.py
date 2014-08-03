# Usage: mitmdump -s "modify_response_body.py mitmproxy bananas"
# (works best with --anticache)

import sys
from libmproxy.protocol.http import decoded


def start(ctx, argv):
    if len(argv) != 3:
        sys.exit('Usage: -s "modify-response-body.py old new"')
    ctx.old, ctx.new = argv[1], argv[2]


def response(ctx, flow):
    with decoded(flow.response):  # automatically decode gzipped responses.
        flow.response.content = flow.response.content.replace(ctx.old, ctx.new)