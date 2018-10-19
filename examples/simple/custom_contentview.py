"""
This example shows how one can add a custom contentview to mitmproxy.
The content view API is explained in the mitmproxy.contentviews module.
"""
from mitmproxy import contentviews


class ViewSwapCase(contentviews.View):
    name = "swapcase"
    media_types = ["text/plain"]

    def __call__(self, data, **metadata) -> contentviews.TViewResult:
        return "case-swapped text", contentviews.format_text(data.swapcase())


view = ViewSwapCase()


def load(l):
    contentviews.add(view)


def done():
    contentviews.remove(view)
