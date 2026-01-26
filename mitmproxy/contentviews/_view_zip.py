import io
import zipfile
from datetime import datetime

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
                    return "# ZIP Archive\nEmpty archive"

                total_compressed = sum(info.compress_size for info in info_list)
                total_uncompressed = sum(info.file_size for info in info_list)

                files_data = {}
                for info in info_list:
                    # compressor_names exists at runtime but not in type stubs
                    compression_names = getattr(zipfile, "compressor_names", {})
                    compression_method = compression_names.get(
                        info.compress_type, f"unknown({info.compress_type})"
                    )

                    file_meta = {
                        "compressed": f"{info.compress_size:,} bytes",
                        "uncompressed": f"{info.file_size:,} bytes",
                        "method": compression_method,
                    }

                    if info.date_time:
                        try:
                            dt = datetime(*info.date_time)
                            file_meta["modified"] = dt.strftime("%Y-%m-%d %H:%M:%S")
                        except (ValueError, OverflowError):
                            pass

                    if info.comment:
                        file_meta["comment"] = info.comment.decode(
                            "utf-8", errors="replace"
                        )

                    files_data[info.filename] = file_meta

                archive_meta = {
                    "Total files": len(info_list),
                    "Total compressed size": f"{total_compressed:,} bytes",
                    "Total uncompressed size": f"{total_uncompressed:,} bytes",
                }

                if total_uncompressed > 0:
                    compression_ratio = (
                        1 - total_compressed / total_uncompressed
                    ) * 100
                    archive_meta["Compression ratio"] = f"{compression_ratio:.1f}%"

                archive_meta["Files"] = files_data

                return "# ZIP Archive\n" + yaml_dumps(archive_meta)

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
