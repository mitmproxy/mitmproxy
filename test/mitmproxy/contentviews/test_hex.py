from mitmproxy.contentviews import hex
from . import full_eval


def test_view_hex():
    v = full_eval(hex.ViewHex())
    assert v(b"foo")
