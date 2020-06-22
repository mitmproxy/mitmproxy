"""
Add a custom message body pretty-printer for use inside mitmproxy.

This example shows how one can add a custom contentview to mitmproxy,
which is used to pretty-print HTTP bodies for example.
The content view API is explained in the mitmproxy.contentviews module.
"""
from mitmproxy import contentviews


class ViewSwapCase(contentviews.View):
    name = "swapcase"
    content_types = ["text/plain"]

    def __call__(self, data, **metadata) -> contentviews.TViewResult:
        return "case-swapped text", contentviews.format_text(data.swapcase())


view = ViewSwapCase()


def load(l):
    contentviews.add(view)


def done():
    contentviews.remove(view)
