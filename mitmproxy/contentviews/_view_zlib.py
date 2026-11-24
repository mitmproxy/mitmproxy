import zlib

from mitmproxy.contentviews._api import Contentview
from mitmproxy.contentviews._api import Metadata


class ZlibContentview(Contentview):
    name = "Zlib"

    def prettify(self, data: bytes, metadata: Metadata) -> str:
        return zlib.decompress(data).decode("utf-8", "backslashreplace")

    def render_priority(self, data: bytes, metadata: Metadata) -> float:
        return 1.0 if data and metadata.content_type == "application/zlib" else 0


zlib_view = ZlibContentview()
