from mitmproxy import contentviews
from mitmproxy.contentviews.api import Contentview, Metadata
from mitmproxy.addonmanager import Loader


class SwapCase(Contentview):
    def prettify(self, data: bytes, metadata: Metadata) -> str:
        return data.swapcase().decode()


view = SwapCase()
def load(loader: Loader):
    contentviews.add(view)
def done():
    contentviews.remove(view)