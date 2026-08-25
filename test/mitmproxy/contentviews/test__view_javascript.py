import pytest

from mitmproxy.contentviews import Metadata
from mitmproxy.contentviews._view_javascript import beautify
from mitmproxy.contentviews._view_javascript import javascript


def test_view_javascript():
    assert javascript.prettify(b"[1, 2, 3]", Metadata())
    assert javascript.prettify(b"[1, 2, 3", Metadata())
    assert javascript.prettify(b"function(a){[1, 2, 3]}", Metadata()) == (
        "function(a) {\n  [1, 2, 3]\n}\n"
    )
    assert javascript.prettify(b"\xfe", Metadata())  # invalid utf-8


@pytest.mark.parametrize(
    "filename",
    [
        "simple.js",
    ],
)
def test_format_xml(filename, tdata):
    path = tdata.path("mitmproxy/contentviews/test_js_data/" + filename)
    with open(path) as f:
        input = f.read()
    with open("-formatted.".join(path.rsplit(".", 1))) as f:
        expected = f.read()
    js = beautify(input)
    assert js == expected


def test_render_priority():
    assert javascript.render_priority(
        b"data", Metadata(content_type="application/x-javascript")
    )
    assert javascript.render_priority(
        b"data", Metadata(content_type="application/javascript")
    )
    assert javascript.render_priority(b"data", Metadata(content_type="text/javascript"))
    assert not javascript.render_priority(b"data", Metadata(content_type="text/plain"))
