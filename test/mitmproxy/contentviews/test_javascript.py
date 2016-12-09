from mitmproxy.contentviews import javascript
from . import full_eval


def test_view_javascript():
    v = full_eval(javascript.ViewJavaScript())
    assert v(b"[1, 2, 3]")
    assert v(b"[1, 2, 3")
    assert v(b"function(a){[1, 2, 3]}")
    assert v(b"\xfe")  # invalid utf-8
