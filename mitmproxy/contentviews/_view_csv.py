import csv
import io

from mitmproxy.contentviews._api import Contentview
from mitmproxy.contentviews._api import Metadata


class CSVContentview(Contentview):
    name = "CSV"

    def prettify(self, data: bytes, metadata: Metadata) -> str:
        text = data.decode("utf-8", "surrogateescape")
        if not text.strip():
            return ""

        delimiter = ","
        if metadata.content_type and (
            "tab-separated" in metadata.content_type or "tsv" in metadata.content_type
        ):
            delimiter = "\t"
        else:
            try:
                sample = "\n".join(text.splitlines()[:5])
                dialect = csv.Sniffer().sniff(sample, delimiters=",\t;")
                delimiter = dialect.delimiter
            except Exception:
                pass

        try:
            reader = csv.reader(io.StringIO(text), delimiter=delimiter)
            rows = [row for row in reader if any(cell.strip() for cell in row)]
        except csv.Error as e:
            raise ValueError(f"Invalid CSV: {e}") from e

        if not rows:
            return ""

        col_count = max(len(row) for row in rows)
        widths = [0] * col_count
        for row in rows:
            for i, cell in enumerate(row):
                widths[i] = max(widths[i], len(cell))

        lines = []
        for row_idx, row in enumerate(rows):
            padded = [
                (row[i] if i < len(row) else "").ljust(widths[i])
                for i in range(col_count)
            ]
            lines.append(" | ".join(padded).rstrip())
            if row_idx == 0 and len(rows) > 1:
                lines.append("-+-".join("-" * w for w in widths))

        return "\n".join(lines) + "\n"

    def render_priority(self, data: bytes, metadata: Metadata) -> float:
        if not data or not metadata.content_type:
            return 0
        if metadata.content_type in (
            "text/csv",
            "text/tab-separated-values",
            "text/tsv",
            "application/csv",
        ):
            return 1
        if metadata.content_type.startswith("text/") and (
            metadata.content_type.endswith("csv")
            or metadata.content_type.endswith("tsv")
        ):
            return 1
        return 0


csv_view = CSVContentview()
