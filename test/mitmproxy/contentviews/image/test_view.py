from mitmproxy.contentviews import image
from .. import full_eval


def test_view_image(tdata):
    v = full_eval(image.ViewImage())
    for img in [
        "mitmproxy/data/image.png",
        "mitmproxy/data/image.gif",
        "mitmproxy/data/all.jpeg",
        "mitmproxy/data/image.ico",
    ]:
        with open(tdata.path(img), "rb") as f:
            viewname, lines = v(f.read())
            assert img.split(".")[-1].upper() in viewname

    assert v(b"flibble") == ('Unknown Image', [[('header', 'Image Format: '), ('text', 'unknown')]])


def test_render_priority():
    v = image.ViewImage()
    assert v.render_priority(b"", content_type="image/png")
    assert v.render_priority(b"", content_type="image/jpeg")
    assert v.render_priority(b"", content_type="image/gif")
    assert v.render_priority(b"", content_type="image/vnd.microsoft.icon")
    assert v.render_priority(b"", content_type="image/x-icon")
    assert v.render_priority(b"", content_type="image/webp")
    assert v.render_priority(b"", content_type="image/future-unknown-format-42")
    assert not v.render_priority(b"", content_type="image/svg+xml")
