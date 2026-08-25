from mitmproxy.contentviews import image
from mitmproxy.contentviews import Metadata


def test_view_image(tdata):
    for img in [
        "mitmproxy/data/image.png",
        "mitmproxy/data/image.gif",
        "mitmproxy/data/all.jpeg",
        "mitmproxy/data/image.ico",
    ]:
        with open(tdata.path(img), "rb") as f:
            desc = image.prettify(f.read(), Metadata())
            assert img.split(".")[-1].upper() in desc

    assert image.prettify(b"flibble", Metadata()) == ("# Unknown Image\n")


def test_render_priority():
    assert image.render_priority(b"", Metadata(content_type="image/png"))
    assert image.render_priority(b"", Metadata(content_type="image/jpeg"))
    assert image.render_priority(b"", Metadata(content_type="image/gif"))
    assert image.render_priority(b"", Metadata(content_type="image/vnd.microsoft.icon"))
    assert image.render_priority(b"", Metadata(content_type="image/x-icon"))
    assert image.render_priority(b"", Metadata(content_type="image/webp"))
    assert image.render_priority(
        b"", Metadata(content_type="image/future-unknown-format-42")
    )
    assert not image.render_priority(b"", Metadata(content_type="image/svg+xml"))
