from . import full_eval
from mitmproxy.contentviews import hex


class TestHexDump:
    def test_view_hex(self):
        v = full_eval(hex.ViewHexDump())
        assert v(b"foo")

    def test_render_priority(self):
        v = hex.ViewHexDump()
        assert not v.render_priority(b"ascii")
        assert v.render_priority(b"\xff")
        assert not v.render_priority(b"")


class TestHexStream:
    def test_view_hex(self):
        v = full_eval(hex.ViewHexStream())
        assert v(b"foo")

    def test_render_priority(self):
        v = hex.ViewHexStream()
        assert not v.render_priority(b"ascii")
        assert v.render_priority(b"\xff")
        assert not v.render_priority(b"")
