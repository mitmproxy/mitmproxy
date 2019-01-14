import io
import re

from mitmproxy.utils import strutils
from mitmproxy.contentviews import base

DELIMITERS = '{};\n'
SPECIAL_AREAS = (
    r"(?<=[^\w\s)])\s*/(?:[^\n/]|(?<!\\)(?:\\\\)*\\/)+?/(?=[gimsuy]{0,6}\s*(?:[;,).\n]|$))",
    r"'" + strutils.MULTILINE_CONTENT_LINE_CONTINUATION + strutils.NO_ESCAPE + "'",
    r'"' + strutils.MULTILINE_CONTENT_LINE_CONTINUATION + strutils.NO_ESCAPE + '"',
    r'`' + strutils.MULTILINE_CONTENT + strutils.NO_ESCAPE + '`',
    r"/\*" + strutils.MULTILINE_CONTENT + r"\*/",
    r"//" + strutils.SINGLELINE_CONTENT + "$",
    r"for\(" + strutils.SINGLELINE_CONTENT + r"\)",
)


def beautify(data):
    data = strutils.escape_special_areas(
        data,
        SPECIAL_AREAS,
        DELIMITERS
    )

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


class ViewJavaScript(base.View):
    name = "JavaScript"
    content_types = [
        "application/x-javascript",
        "application/javascript",
        "text/javascript"
    ]

    def __call__(self, data, **metadata):
        data = data.decode("utf-8", "replace")
        res = beautify(data)
        return "JavaScript", base.format_text(res)
