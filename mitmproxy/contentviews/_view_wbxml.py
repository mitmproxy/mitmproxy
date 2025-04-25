from mitmproxy.contentviews._api import Contentview
from mitmproxy.contentviews._api import Metadata
from mitmproxy.contrib.wbxml import ASCommandResponse


class WBXMLContentview(Contentview):
    __content_types = ("application/vnd.wap.wbxml", "application/vnd.ms-sync.wbxml")
    syntax_highlight = "xml"

    def prettify(
        self,
        data: bytes,
        metadata: Metadata,
    ) -> str:
        return ASCommandResponse.ASCommandResponse(data).xmlString

    def render_priority(
        self,
        data: bytes,
        metadata: Metadata,
    ) -> float:
        return float(bool(data) and metadata.content_type in self.__content_types)


wbxml = WBXMLContentview()
