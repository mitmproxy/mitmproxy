from mitmproxy.contrib.wbxml import ASCommandResponse
from . import base


class ViewWBXML(base.View):
    name = "WBXML"
    content_types = [
        "application/vnd.wap.wbxml",
        "application/vnd.ms-sync.wbxml"
    ]

    def __call__(self, data, **metadata):
        try:
            parser = ASCommandResponse.ASCommandResponse(data)
            parsedContent = parser.xmlString
            if parsedContent:
                return "WBXML", base.format_text(parsedContent)
        except:
            return None
