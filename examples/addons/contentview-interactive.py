from mitmproxy import contentviews
from mitmproxy.contentviews._api import Contentview, Metadata, InteractiveContentview
from mitmproxy.addonmanager import Loader


class InteractiveSwapCase(InteractiveContentview):
    def prettify(
        self, 
        data: bytes, 
        metadata: Metadata,
    ) -> str:
        return data.swapcase().decode()

    def reencode(
        self, 
        prettified: str, 
        metadata: Metadata,
    ) -> bytes:
        return prettified.encode().swapcase()


view = InteractiveSwapCase()
def load(loader: Loader):
    contentviews.add(view)
def done():
    contentviews.remove(view) 