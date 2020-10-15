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

def test_should_render():
    v = javascript.ViewJavaScript()
    assert v.should_render("application/x-javascript")
    assert v.should_render("application/javascript")
    assert v.should_render("text/javascript")
    assert not v.should_render("text/plain")
