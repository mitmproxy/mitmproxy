import re
import time

from mitmproxy.contentviews import base
from mitmproxy.utils import strutils

"""
A custom CSS prettifier. Compared to other prettifiers, its main features are:

- Implemented in pure Python.
- Modifies whitespace only.
- Works with any input.
- Considerably faster than e.g. cssutils.
"""

CSS_SPECIAL_AREAS = (
    "'" + strutils.SINGLELINE_CONTENT + strutils.NO_ESCAPE + "'",
    '"' + strutils.SINGLELINE_CONTENT + strutils.NO_ESCAPE + '"',
    r"/\*" + strutils.MULTILINE_CONTENT + r"\*/",
    "//" + strutils.SINGLELINE_CONTENT + "$"
)
CSS_SPECIAL_CHARS = "{};:"


def beautify(data: str, indent: str = "    "):
    """Beautify a string containing CSS code"""
    data = strutils.escape_special_areas(
        data.strip(),
        CSS_SPECIAL_AREAS,
        CSS_SPECIAL_CHARS,
    )

    # Add newlines
    data = re.sub(r"\s*;\s*", ";\n", data)
    data = re.sub(r"\s*{\s*", " {\n", data)
    data = re.sub(r"\s*}\s*", "\n}\n\n", data)

    # Fix incorrect ":" placement
    data = re.sub(r"\s*:\s*(?=[^{]+})", ": ", data)
    # Fix no space after ","
    data = re.sub(r"\s*,\s*", ", ", data)

    # indent
    data = re.sub("\n[ \t]+", "\n", data)
    data = re.sub("\n(?![}\n])(?=[^{]*})", "\n" + indent, data)

    data = strutils.unescape_special_areas(data)
    return data.rstrip("\n") + "\n"


class ViewCSS(base.View):
    name = "CSS"
    content_types = [
        "text/css"
    ]

    def __call__(self, data, **metadata):
        data = data.decode("utf8", "surrogateescape")
        beautified = beautify(data)
        return "CSS", base.format_text(beautified)


if __name__ == "__main__":  # pragma: no cover
    with open("../tools/web/static/vendor.css") as f:
        data = f.read()

    t = time.time()
    x = beautify(data)
    print("Beautifying vendor.css took {:.2}s".format(time.time() - t))
