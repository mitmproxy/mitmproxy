import io
import zipfile

from mitmproxy.contentviews._api import Contentview, Metadata
from mitmproxy.contentviews._utils import yaml_dumps


class ZipContentview(Contentview):
    name = "ZIP Archive"
    syntax_highlight = "yaml"

    def prettify(self, data: bytes, metadata: Metadata) -> str:
        with zipfile.ZipFile(io.BytesIO(data), "r") as zip_file:
            filenames = [info.filename for info in zip_file.infolist()]
            return yaml_dumps(filenames) if filenames else "(empty zip file)"

    def render_priority(self, data: bytes, metadata: Metadata) -> float:
        return 1.0 if data and metadata.content_type == "application/zip" else 0


zip = ZipContentview()
