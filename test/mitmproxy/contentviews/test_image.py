from mitmproxy.contentviews.image import pillow
from mitmproxy.test import tutils
from . import full_eval


def test_view_image():
    v = full_eval(pillow.ViewImage())
    for img in [
        "mitmproxy/data/image.png",
        "mitmproxy/data/image.gif",
        "mitmproxy/data/image-err1.jpg",
        "mitmproxy/data/image.ico"
    ]:
        with open(tutils.test_data.path(img), "rb") as f:
            assert v(f.read())

    assert not v(b"flibble")
