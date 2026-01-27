import io
import zipfile
from datetime import datetime

from mitmproxy.contentviews._api import Contentview
from mitmproxy.contentviews._api import Metadata


def _get_compression_method_name(info: zipfile.ZipInfo) -> str:
    """Get human-readable compression method name."""
    method = info.compress_type
    method_names = getattr(zipfile, "compressor_names", {})
    if method in method_names:
        return method_names[method]
    # Fallback for common methods
    if method == zipfile.ZIP_STORED:
        return "Stored"
    elif method == zipfile.ZIP_DEFLATED:
        return "Deflated"
    elif method == zipfile.ZIP_BZIP2:
        return "BZip2"
    elif method == zipfile.ZIP_LZMA:
        return "LZMA"
    else:
        return f"Method {method}"


class ZipContentview(Contentview):
    name = "ZIP Archive"
    syntax_highlight = "none"

    def prettify(self, data: bytes, metadata: Metadata) -> str:
        try:
            with zipfile.ZipFile(io.BytesIO(data), "r") as zip_file:
                info_list = zip_file.infolist()

                if not info_list:
                    return "ZIP Archive\nEmpty archive"

                # Collect file information
                file_rows = []
                total_length = 0

                for info in info_list:
                    length = info.file_size
                    total_length += length

                    # Format date and time
                    date_str = ""
                    time_str = ""
                    if info.date_time:
                        try:
                            dt = datetime(*info.date_time)
                            date_str = dt.strftime("%Y-%m-%d")
                            time_str = dt.strftime("%H:%M")
                        except (ValueError, OverflowError):
                            pass

                    file_rows.append((length, date_str, time_str, info.filename))

                # Calculate column widths - match unzip -l format
                # Length column: right-aligned, at least 9 chars (for "Length" header)
                max_length = max(len(str(row[0])) for row in file_rows) if file_rows else 1
                max_length = max(max_length, 9)
                # Build output matching unzip -l format
                lines = []
                # Header
                header = f"  Length      Date    Time    Name"
                lines.append(header)
                # Separator
                separator = "---------  ---------- -----   ----"
                lines.append(separator)
                # File rows
                for length, date, time, filename in file_rows:
                    date_pad = date if date else "          "  # 10 spaces
                    time_pad = time if time else "     "  # 5 spaces
                    row = f"{length:>9}  {date_pad:<10} {time_pad:<5}   {filename}"
                    lines.append(row)
                # Summary separator
                lines.append("---------                     -------")
                # Summary line
                summary = f"{total_length:>9}                      {len(file_rows)} file{'s' if len(file_rows) != 1 else ''}"
                lines.append(summary)
                return "\n".join(lines)

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


class ZipVerboseContentview(Contentview):
    name = "ZIP Archive (verbose)"
    syntax_highlight = "none"

    def prettify(self, data: bytes, metadata: Metadata) -> str:
        try:
            with zipfile.ZipFile(io.BytesIO(data), "r") as zip_file:
                info_list = zip_file.infolist()

                if not info_list:
                    return "ZIP Archive (verbose)\nEmpty archive"

                # Collect file information with verbose details
                file_rows = []
                total_length = 0
                total_compressed = 0

                for info in info_list:
                    length = info.file_size
                    compressed = info.compress_size
                    total_length += length
                    total_compressed += compressed

                    # Calculate compression ratio
                    if length > 0:
                        ratio = (1 - compressed / length) * 100
                    else:
                        ratio = 0.0
                    # Format date and time
                    date_str = ""
                    time_str = ""
                    if info.date_time:
                        try:
                            dt = datetime(*info.date_time)
                            date_str = dt.strftime("%Y-%m-%d")
                            time_str = dt.strftime("%H:%M")
                        except (ValueError, OverflowError):
                            pass

                    method = _get_compression_method_name(info)
                    crc = info.CRC
                    file_rows.append((
                        length, compressed, ratio, method, crc, date_str, time_str, info.filename
                    ))
                # Calculate column widths
                max_length = max(len(str(row[0])) for row in file_rows) if file_rows else 1
                max_length = max(max_length, 9)
                max_compressed = max(len(str(row[1])) for row in file_rows) if file_rows else 1
                max_compressed = max(max_compressed, 9)
                max_method = max(len(row[3]) for row in file_rows) if file_rows else 1
                max_method = max(max_method, len("Method"))

                # Build output matching unzip -l -v format
                lines = []

                # Header
                header = f" Length   Method    Size  Cmpr    Date    Time   CRC-32   Name"
                lines.append(header)
                
                # Separator
                separator = "--------  ------  ------- ---- ---------- ----- --------  ----"
                lines.append(separator)

                # File rows
                for length, compressed, ratio, method, crc, date, time, filename in file_rows:
                    date_pad = date if date else "          "
                    time_pad = time if time else "     "
                    ratio_str = f"{ratio:.0f}%" if ratio > 0 else "  0%"
                    crc_str = f"{crc:08x}"
                    row = (
                        f"{length:>8}  {method:<{max_method}} {compressed:>7} {ratio_str:>4} "
                        f"{date_pad:<10} {time_pad:<5} {crc_str}   {filename}"
                    )
                    lines.append(row)

                # Summary separator
                lines.append("--------          ------- ---                            -------")

                # Summary line
                total_ratio = (1 - total_compressed / total_length) * 100 if total_length > 0 else 0.0
                ratio_str = f"{total_ratio:.0f}%" if total_ratio > 0 else "  0%"
                summary = (
                    f"{total_length:>8}          {total_compressed:>7} {ratio_str:>4} "
                    f"                            {len(file_rows)} file{'s' if len(file_rows) != 1 else ''}"
                )
                lines.append(summary)

                return "\n".join(lines)

        except zipfile.BadZipFile:
            raise ValueError("Invalid or corrupted ZIP file")
        except Exception as e:
            raise ValueError(f"Error parsing ZIP file: {e}")

    def render_priority(self, data: bytes, metadata: Metadata) -> float:
        if not data:
            return 0
        if metadata.content_type == "application/zip":
            return 0.9  # Lower priority than regular ZIP view
        return 0


zip = ZipContentview()
zip_verbose = ZipVerboseContentview()