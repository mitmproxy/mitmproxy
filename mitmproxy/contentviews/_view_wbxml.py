from mitmproxy.contentviews._api import Contentview
from mitmproxy.contentviews._api import Metadata
from mitmproxy.contentviews._api import SyntaxHighlight
from mitmproxy.contrib.wbxml import ASCommandResponse


class WBXMLContentview(Contentview):
    __content_types = ("application/vnd.wap.wbxml", "application/vnd.ms-sync.wbxml")

    @property
    def syntax_highlight(self) -> SyntaxHighlight:
        return "xml"

    def prettify(
        self,
        data: bytes,
        metadata: Metadata,
    ) -> str:
        return ASCommandResponse.ASCommandResponse(data).xmlString or ""

    def render_priority(
        self,
        data: bytes,
        metadata: Metadata,
    ) -> float:
        return float(bool(data) and metadata.content_type in self.__content_types)


wbxml = WBXMLContentview()
