from mitmproxy.contentviews import raw
from . import full_eval


def test_view_raw():
    v = full_eval(raw.ViewRaw())
    assert v(b"foo")
