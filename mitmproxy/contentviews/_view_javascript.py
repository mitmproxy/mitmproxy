import io
import re

from mitmproxy.contentviews._api import Contentview
from mitmproxy.contentviews._api import Metadata
from mitmproxy.utils import strutils

DELIMITERS = "{};\n"
SPECIAL_AREAS = (
    r"(?<=[^\w\s)])\s*/(?:[^\n/]|(?<!\\)(?:\\\\)*\\/)+?/(?=[gimsuy]{0,6}\s*(?:[;,).\n]|$))",
    r"'" + strutils.MULTILINE_CONTENT_LINE_CONTINUATION + strutils.NO_ESCAPE + "'",
    r'"' + strutils.MULTILINE_CONTENT_LINE_CONTINUATION + strutils.NO_ESCAPE + '"',
    r"`" + strutils.MULTILINE_CONTENT + strutils.NO_ESCAPE + "`",
    r"/\*" + strutils.MULTILINE_CONTENT + r"\*/",
    r"//" + strutils.SINGLELINE_CONTENT + "$",
    r"for\(" + strutils.SINGLELINE_CONTENT + r"\)",
)


def beautify(data):
    data = strutils.escape_special_areas(data, SPECIAL_AREAS, DELIMITERS)

    data = re.sub(r"\s*{\s*(?!};)", " {\n", data)
    data = re.sub(r"\s*;\s*", ";\n", data)
    data = re.sub(r"(?<!{)\s*}(;)?\s*", r"\n}\1\n", data)

    beautified = io.StringIO()
    indent_level = 0

    for line in data.splitlines(True):
        if line.endswith("{\n"):
            beautified.write(" " * 2 * indent_level + line)
            indent_level += 1
        elif line.startswith("}"):
            indent_level -= 1
            beautified.write(" " * 2 * indent_level + line)
        else:
            beautified.write(" " * 2 * indent_level + line)

    data = strutils.unescape_special_areas(beautified.getvalue())
    return data


class JavaScriptContentview(Contentview):
    syntax_highlight = "javascript"
    __content_types = (
        "application/x-javascript",
        "application/javascript",
        "text/javascript",
    )

    def prettify(
        self,
        data: bytes,
        metadata: Metadata,
    ) -> str:
        data_str = data.decode("utf-8", "replace")
        return beautify(data_str)

    def render_priority(
        self,
        data: bytes,
        metadata: Metadata,
    ) -> float:
        return float(bool(data) and metadata.content_type in self.__content_types)


javascript = JavaScriptContentview()
