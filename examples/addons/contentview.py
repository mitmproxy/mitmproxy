from mitmproxy import contentviews
from mitmproxy.addonmanager import Loader
from mitmproxy.contentviews._api import Contentview
from mitmproxy.contentviews._api import Metadata


class SwapCase(Contentview):
    def prettify(self, data: bytes, metadata: Metadata) -> str:
        return data.swapcase().decode()


view = SwapCase()


def load(loader: Loader):
    contentviews.add(view)


def done():
    contentviews.remove(view)
