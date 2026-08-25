from mitmproxy.contentviews import Metadata
from mitmproxy.contentviews._view_urlencoded import urlencoded
from mitmproxy.net.http import url


def test_view_urlencoded():
    d = url.encode([("one", "two"), ("three", "four")]).encode()
    assert urlencoded.prettify(d, Metadata()) == "one: two\nthree: four\n"

    d = url.encode([("adsfa", "")]).encode()
    assert urlencoded.prettify(d, Metadata()) == "adsfa: ''\n"

    assert urlencoded.prettify(b"\xff\x00", Metadata()) == "\\xff\\x00: ''\n"


def test_render_priority():
    assert urlencoded.render_priority(
        b"data", Metadata(content_type="application/x-www-form-urlencoded")
    )
    assert not urlencoded.render_priority(b"data", Metadata(content_type="text/plain"))
