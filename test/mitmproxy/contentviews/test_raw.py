from . import full_eval
from mitmproxy.contentviews import raw


def test_view_raw():
    v = full_eval(raw.ViewRaw())
    assert v(b"foo")
    assert v("\\©".encode()) == (
        "Raw",
        [[("text", "\\©".encode())]],
    )


def test_render_priority():
    v = raw.ViewRaw()
    assert v.render_priority(b"anything")
    assert not v.render_priority(b"")
