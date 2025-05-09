from mitmproxy.contentviews._api import InteractiveContentview
from mitmproxy.contentviews._api import Metadata
from mitmproxy.contentviews._utils import yaml_dumps
from mitmproxy.contentviews._utils import yaml_loads
from mitmproxy.dns import DNSMessage as DNSMessage
from mitmproxy.proxy.layers.dns import pack_message


def _is_dns_tcp(metadata: Metadata) -> bool:
    return bool(metadata.tcp_message or metadata.http_message)


class DNSContentview(InteractiveContentview):
    syntax_highlight = "yaml"

    def prettify(
        self,
        data: bytes,
        metadata: Metadata,
    ) -> str:
        if _is_dns_tcp(metadata):
            data = data[2:]  # hack: cut off length label and hope for the best
        message = DNSMessage.unpack(data).to_json()
        del message["status_code"]
        message.pop("timestamp", None)
        return yaml_dumps(message)

    def reencode(
        self,
        prettified: str,
        metadata: Metadata,
    ) -> bytes:
        data = yaml_loads(prettified)
        message = DNSMessage.from_json(data)
        return pack_message(message, "tcp" if _is_dns_tcp(metadata) else "udp")

    def render_priority(
        self,
        data: bytes,
        metadata: Metadata,
    ) -> float:
        return float(
            metadata.content_type == "application/dns-message"
            or bool(
                metadata.flow
                and metadata.flow.server_conn
                and metadata.flow.server_conn.address
                and metadata.flow.server_conn.address[1] in (53, 5353)
            )
        )


dns = DNSContentview()
