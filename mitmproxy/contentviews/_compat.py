from __future__ import  annotations
import typing
from typing import Iterator

from mitmproxy.contentviews.api import Contentview, Metadata
from mitmproxy.utils.strutils import always_str

if typing.TYPE_CHECKING:
    from mitmproxy.contentviews.base import TViewLine, View

class LegacyContentview(Contentview):
    @property
    def name(self) -> str:
        return self.contentview.name

    def render_priority(
        self,
        data: bytes,
        metadata: Metadata,
    ) -> float | None:
        return self.contentview.render_priority(
            data=data,
            content_type=metadata.content_type,
            flow=metadata.flow,
            http_message=metadata.http_message
        )

    def prettify(self, data: bytes, metadata: Metadata) -> str:
        lines: Iterator[TViewLine]
        desc_, lines = self.contentview(
            data,
            content_type=metadata.content_type,
            flow=metadata.flow,
            http_message=metadata.http_message
        )
        return "\n".join(
            "".join(
                always_str(text, "utf8", "backslashescape")
                for tag, text in line
            )
            for line in lines
        )

    def __init__(self, contentview: View):
        self.contentview = contentview

