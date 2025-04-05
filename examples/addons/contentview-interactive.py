from mitmproxy import contentviews
from mitmproxy.addonmanager import Loader
from mitmproxy.contentviews._api import InteractiveContentview
from mitmproxy.contentviews._api import Metadata


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
