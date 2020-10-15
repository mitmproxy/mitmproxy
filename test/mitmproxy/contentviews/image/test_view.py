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

def test_should_render():
    v = image.ViewImage()
    assert v.should_render("image/png")
    assert v.should_render("image/jpeg")
    assert v.should_render("image/gif")
    assert v.should_render("image/vnd.microsoft.icon")
    assert v.should_render("image/x-icon")
    assert v.should_render("image/webp")
    assert not v.should_render("image/svg+xml")
