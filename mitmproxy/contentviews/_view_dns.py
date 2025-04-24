from mitmproxy.contentviews._api import Contentview
from mitmproxy.contentviews._api import Metadata
from mitmproxy.contentviews._utils import yaml_dumps
from mitmproxy.dns import Message as DNSMessage


class DNSContentview(Contentview):
    syntax_highlight = "yaml"

    def prettify(
        self,
        data: bytes,
        metadata: Metadata,
    ) -> str:
        message = DNSMessage.unpack(data)
        return yaml_dumps(message.to_json())

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
