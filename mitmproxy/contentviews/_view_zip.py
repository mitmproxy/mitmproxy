import io
import zipfile

from mitmproxy.contentviews._api import Contentview
from mitmproxy.contentviews._api import Metadata
from mitmproxy.contentviews._utils import yaml_dumps


class ZipContentview(Contentview):
    name = "ZIP Archive"
    syntax_highlight = "yaml"

    def prettify(self, data: bytes, metadata: Metadata) -> str:
        try:
            with zipfile.ZipFile(io.BytesIO(data), "r") as zip_file:
                info_list = zip_file.infolist()

                if not info_list:
                    return yaml_dumps([])

                files = self._extract_file_info(info_list)
                return yaml_dumps(files)

        except zipfile.BadZipFile:
            raise ValueError("Invalid or corrupted ZIP file")
        except Exception as e:
            raise ValueError(f"Error parsing ZIP file: {e}")

    def _extract_file_info(self, info_list: list[zipfile.ZipInfo]) -> list[dict[str, int | str]]:
        files = []
        for info in info_list:
            file_info: dict[str, int | str] = {"filename": info.filename}
            if info.file_size > 0:
                file_info["size"] = info.file_size
            files.append(file_info)
        return files

    def render_priority(self, data: bytes, metadata: Metadata) -> float:
        if not data:
            return 0
        if metadata.content_type == "application/zip":
            return 1.0
        return 0


zip = ZipContentview()
