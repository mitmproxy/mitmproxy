# (this script works best with --anticache)
from bs4 import BeautifulSoup


class Injector:
    def __init__(self):
        self.iframe_url = None

    def load(self, loader):
        loader.add_option(
            "iframe", str, "", "IFrame to inject"
        )

    def configure(self, options, updated):
        self.iframe_url = options.iframe

    def response(self, flow):
        if self.iframe_url:
            html = BeautifulSoup(flow.response.content, "html.parser")
            if html.body:
                iframe = html.new_tag(
                    "iframe",
                    src=self.iframe_url,
                    frameborder=0,
                    height=0,
                    width=0)
                html.body.insert(0, iframe)
                flow.response.content = str(html).encode("utf8")


addons = [Injector()]
