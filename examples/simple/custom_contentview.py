"""
This example shows how one can add a custom contentview to mitmproxy.
The content view API is explained in the mitmproxy.contentviews module.
"""
from mitmproxy import contentviews
import typing


CVIEWSWAPCASE = typing.Tuple[str, typing.Iterable[typing.List[typing.Tuple[str, typing.AnyStr]]]]


class ViewSwapCase(contentviews.View):
    name = "swapcase"

    # We don't have a good solution for the keyboard shortcut yet -
    # you manually need to find a free letter. Contributions welcome :)
    prompt = ("swap case text", "t")
    content_types = ["text/plain"]

    def __call__(self, data: typing.AnyStr, **metadata) -> CVIEWSWAPCASE:
        return "text", contentviews.format_text(data.swapcase())


view = ViewSwapCase()


contentviews.add(view)
