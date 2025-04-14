from mitmproxy.contentviews._view_raw import raw
from mitmproxy.contentviews._api import Metadata


def test_view_raw():
    meta = Metadata()
    assert raw.prettify(b"foo", meta)
    # unicode
    assert raw.prettify("🫠".encode(), meta) == "🫠"
    # invalid utf8
    assert raw.prettify(b"\xff", meta) == r"\xff"


def test_render_priority():
    assert raw.render_priority(b"data", Metadata()) == 0
