"""
Add a custom message body pretty-printer for use inside mitmproxy.

This example shows how one can add a custom contentview to mitmproxy,
which is used to pretty-print HTTP bodies for example.
The content view API is explained in the mitmproxy.contentviews module.
"""

from mitmproxy import contentviews
from mitmproxy import flow
from mitmproxy import http
from mitmproxy.addonmanager import Loader


class ViewSwapCase(contentviews.View):
    name = "swapcase"

    def __call__(
        self,
        data: bytes,
        *,
        content_type: str | None = None,
        flow: flow.Flow | None = None,
        http_message: http.Message | None = None,
        **unknown_metadata,
    ) -> contentviews.TViewResult:
        return "case-swapped text", contentviews.format_text(data.swapcase())

    def render_priority(
        self,
        data: bytes,
        *,
        content_type: str | None = None,
        flow: flow.Flow | None = None,
        http_message: http.Message | None = None,
        **unknown_metadata,
    ) -> float:
        if content_type == "text/plain":
            return 1
        else:
            return 0


view = ViewSwapCase()


def load(loader: Loader):
    contentviews.add(view)


def done():
    contentviews.remove(view)
