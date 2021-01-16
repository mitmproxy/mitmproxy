"""
Add a custom message body pretty-printer for use inside mitmproxy.

This example shows how one can add a custom contentview to mitmproxy,
which is used to pretty-print HTTP bodies for example.
The content view API is explained in the mitmproxy.contentviews module.
"""
from typing import Optional

from mitmproxy import contentviews, flow, http


class ViewSwapCase(contentviews.View):
    name = "swapcase"

    def __call__(self, data, **metadata) -> contentviews.TViewResult:
        return "case-swapped text", contentviews.format_text(data.swapcase())

    def render_priority(
        self,
        data: bytes,
        *,
        content_type: Optional[str] = None,
        flow: Optional[flow.Flow] = None,
        http_message: Optional[http.HTTPMessage] = None,
        **unknown_metadata,
    ) -> float:
        return float(content_type == "text/plain")


view = ViewSwapCase()


def load(l):
    contentviews.add(view)


def done():
    contentviews.remove(view)
