"""
This example shows how one can add a custom contentview to mitmproxy.
The content view API is explained in the mitmproxy.contentviews module.
"""
from mitmproxy import contentviews


class ViewSwapCase(contentviews.View):
    name = "swapcase"

    # We don't have a good solution for the keyboard shortcut yet -
    # you manually need to find a free letter. Contributions welcome :)
    prompt = ("swap case text", "z")
    content_types = ["text/plain"]

    def __call__(self, data: bytes, **metadata):
        return "case-swapped text", contentviews.format_text(data.swapcase())


view = ViewSwapCase()


def start():
    old_view = contentviews.get(view.name)
    if old_view is not None:
        contentviews.remove(old_view)
    contentviews.add(view)

def done():
    contentviews.remove(view)
