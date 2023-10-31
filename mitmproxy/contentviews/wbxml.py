from . import base
from mitmproxy.contrib.wbxml import ASCommandResponse


class ViewWBXML(base.View):
    name = "WBXML"
    __content_types = ("application/vnd.wap.wbxml", "application/vnd.ms-sync.wbxml")

    def __call__(self, data, **metadata):
        try:
            parser = ASCommandResponse.ASCommandResponse(data)
            parsedContent = parser.xmlString
            if parsedContent:
                return "WBXML", base.format_text(parsedContent)
        except Exception:
            return None

    def render_priority(
        self, data: bytes, *, content_type: str | None = None, **metadata
    ) -> float:
        return float(bool(data) and content_type in self.__content_types)
