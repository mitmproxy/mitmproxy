from typing import Optional

from . import base
from .. import http


class ViewQuery(base.View):
    name = "Query"

    def __call__(self, data: bytes, http_message: Optional[http.Message] = None, **metadata):
        query = getattr(http_message, "query", None)
        if query:
            return "Query", base.format_pairs(query.items(multi=True))
        else:
            return "Query", base.format_text("")

    def render_priority(self, data: bytes, *, http_message: Optional[http.Message] = None, **metadata) -> float:
        return 0.3 * float(bool(
            getattr(http_message, "query", False)
            and not data
        ))
