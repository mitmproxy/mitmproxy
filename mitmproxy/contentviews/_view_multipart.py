from ._utils import byte_pairs_to_str_pairs
from ._utils import merge_repeated_keys
from ._utils import yaml_dumps
from mitmproxy.contentviews._api import Contentview
from mitmproxy.contentviews._api import Metadata
from mitmproxy.net.http.multipart import decode_multipart


class MultipartContentview(Contentview):
    name = "Multipart Form"
    syntax_highlight = "yaml"

    def prettify(
        self,
        data: bytes,
        metadata: Metadata,
    ) -> str:
        if not metadata.http_message:
            raise ValueError("Not an HTTP message")
        content_type = metadata.http_message.headers["content-type"]
        items = decode_multipart(content_type, data)
        return yaml_dumps(merge_repeated_keys(byte_pairs_to_str_pairs(items)))

    def render_priority(
        self,
        data: bytes,
        metadata: Metadata,
    ) -> float:
        return float(bool(data) and metadata.content_type == "multipart/form-data")


multipart = MultipartContentview()
