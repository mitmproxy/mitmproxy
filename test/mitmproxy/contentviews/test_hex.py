from mitmproxy.contentviews import hex
from . import full_eval


def test_view_hex():
    v = full_eval(hex.ViewHex())
    assert v(b"foo")


def test_render_priority():
    v = hex.ViewHex()
    assert not v.render_priority(b"ascii")
    assert v.render_priority(b"\xFF")
    assert not v.render_priority(b"")
