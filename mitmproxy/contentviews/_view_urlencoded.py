import urllib
import urllib.parse

from ._utils import byte_pairs_to_str_pairs
from ._utils import merge_repeated_keys
from ._utils import yaml_dumps
from mitmproxy.contentviews._api import Contentview
from mitmproxy.contentviews._api import Metadata


class URLEncodedContentview(Contentview):
    name = "URL-encoded"
    syntax_highlight = "yaml"

    def prettify(
        self,
        data: bytes,
        metadata: Metadata,
    ) -> str:
        items = urllib.parse.parse_qsl(data, keep_blank_values=True)
        return yaml_dumps(merge_repeated_keys(byte_pairs_to_str_pairs(items)))

    def render_priority(
        self,
        data: bytes,
        metadata: Metadata,
    ) -> float:
        return float(
            bool(data) and metadata.content_type == "application/x-www-form-urlencoded"
        )


urlencoded = URLEncodedContentview()
