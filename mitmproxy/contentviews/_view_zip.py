import io
import zipfile

from mitmproxy.contentviews._api import Contentview
from mitmproxy.contentviews._api import Metadata


class ZipContentview(Contentview):
    name = "ZIP Archive"
    syntax_highlight = "yaml"

    def prettify(self, data: bytes, metadata: Metadata) -> str:
        try:
            with zipfile.ZipFile(io.BytesIO(data), "r") as zip_file:
                info_list = zip_file.infolist()
                lines = [
                    f"- filename: {info.filename}, size: {info.file_size}"
                    for info in info_list
                ]
                return "\n".join(lines) + "\n" if lines else ""
        except zipfile.BadZipFile:
            raise ValueError("Invalid or corrupted ZIP file")
        except Exception as e:
            raise ValueError(f"Error parsing ZIP file: {e}")

    def render_priority(self, data: bytes, metadata: Metadata) -> float:
        if not data:
            return 0
        if metadata.content_type == "application/zip":
            return 1.0
        return 0


zip = ZipContentview()
