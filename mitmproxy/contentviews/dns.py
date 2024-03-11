from mitmproxy.contentviews import base
from mitmproxy.contentviews.json import format_json
from mitmproxy.dns import Message


class ViewDns(base.View):
    name = "DNS-over-HTTPS"

    def __call__(self, data, **metadata):
        try:
            message = Message.unpack(data)
        except Exception:
            pass
        else:
            return "DoH", format_json(message.to_json())

    def render_priority(
        self, data: bytes, *, content_type: str | None = None, **metadata
    ) -> float:
        return float(content_type == "application/dns-message")
