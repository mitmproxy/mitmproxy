import pytest

from mitmproxy.contentviews import Metadata
from mitmproxy.contentviews._view_css import css


@pytest.mark.parametrize(
    "filename",
    [
        "animation-keyframe.css",
        "blank-lines-and-spaces.css",
        "block-comment.css",
        "empty-rule.css",
        "import-directive.css",
        "indentation.css",
        "media-directive.css",
        "quoted-string.css",
        "selectors.css",
        "simple.css",
    ],
)
def test_beautify(filename, tdata):
    path = tdata.path("mitmproxy/contentviews/test_css_data/" + filename)
    with open(path, "rb") as f:
        input = f.read()
    with open("-formatted.".join(path.rsplit(".", 1))) as f:
        expected = f.read()
    formatted = css.prettify(input, Metadata())
    assert formatted == expected


def test_simple():
    meta = Metadata()
    assert css.prettify(b"#foo{color:red}", meta) == "#foo {\n    color: red\n}\n"
    assert css.prettify(b"", meta) == "\n"
    assert (
        css.prettify(b"console.log('not really css')", meta)
        == "console.log('not really css')\n"
    )


def test_render_priority():
    assert css.render_priority(b"data", Metadata(content_type="text/css"))
    assert not css.render_priority(b"data", Metadata(content_type="text/plain"))
