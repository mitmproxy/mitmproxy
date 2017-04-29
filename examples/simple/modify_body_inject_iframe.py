# (this script works best with --anticache)
from bs4 import BeautifulSoup
from mitmproxy import ctx, http


class Injector:
    def load(self, loader):
        loader.add_option(
            "iframe", str, "", "IFrame to inject"
        )

    def response(self, flow: http.HTTPFlow) -> None:
        if ctx.options.iframe:
            html = BeautifulSoup(flow.response.content, "html.parser")
            if html.body:
                iframe = html.new_tag(
                    "iframe",
                    src=ctx.options.iframe,
                    frameborder=0,
                    height=0,
                    width=0)
                html.body.insert(0, iframe)
                flow.response.content = str(html).encode("utf8")


addons = [Injector()]
