import re
import time

from mitmproxy.contentviews._api import Contentview
from mitmproxy.contentviews._api import Metadata
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
    "//" + strutils.SINGLELINE_CONTENT + "$",
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


class ViewCSS(Contentview):
    syntax_highlight = "css"

    def prettify(self, data: bytes, metadata: Metadata) -> str:
        data_str = data.decode("utf8", "surrogateescape")
        return beautify(data_str)

    def render_priority(
        self,
        data: bytes,
        metadata: Metadata,
    ) -> float:
        return float(bool(data) and metadata.content_type == "text/css")


css = ViewCSS()


if __name__ == "__main__":  # pragma: no cover
    with open("../tools/web/static/vendor.css") as f:
        data = f.read()

    t = time.time()
    x = beautify(data)
    print(f"Beautifying vendor.css took {time.time() - t:.2}s")
