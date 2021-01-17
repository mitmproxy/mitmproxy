import pytest

from mitmproxy.contentviews import javascript
from . import full_eval


def test_view_javascript():
    v = full_eval(javascript.ViewJavaScript())
    assert v(b"[1, 2, 3]")
    assert v(b"[1, 2, 3")
    assert v(b"function(a){[1, 2, 3]}") == ("JavaScript", [
        [('text', 'function(a) {')],
        [('text', '  [1, 2, 3]')],
        [('text', '}')]
    ])
    assert v(b"\xfe")  # invalid utf-8


@pytest.mark.parametrize("filename", [
    "simple.js",
])
def test_format_xml(filename, tdata):
    path = tdata.path("mitmproxy/contentviews/test_js_data/" + filename)
    with open(path) as f:
        input = f.read()
    with open("-formatted.".join(path.rsplit(".", 1))) as f:
        expected = f.read()
    js = javascript.beautify(input)
    assert js == expected


def test_render_priority():
    v = javascript.ViewJavaScript()
    assert v.render_priority(b"", content_type="application/x-javascript")
    assert v.render_priority(b"", content_type="application/javascript")
    assert v.render_priority(b"", content_type="text/javascript")
    assert not v.render_priority(b"", content_type="text/plain")
