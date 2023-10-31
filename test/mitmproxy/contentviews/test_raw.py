from mitmproxy.contentviews import raw

from . import full_eval


def test_view_raw():
    v = full_eval(raw.ViewRaw())
    assert v(b"foo")
    # unicode
    assert v("🫠".encode()) == (
        "Raw",
        [[("text", "🫠".encode())]],
    )
    # invalid utf8
    assert v(b"\xFF") == (
        "Raw",
        [[("text", b"\xFF")]],
    )


def test_render_priority():
    v = raw.ViewRaw()
    assert v.render_priority(b"anything")
    assert not v.render_priority(b"")
