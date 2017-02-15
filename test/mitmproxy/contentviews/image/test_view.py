from mitmproxy.contentviews import image
from mitmproxy.test import tutils
from .. import full_eval


def test_view_image():
    v = full_eval(image.ViewImage())
    for img in [
        "mitmproxy/data/image.png",
        "mitmproxy/data/image.gif",
        "mitmproxy/data/all.jpeg",
        # https://bugs.python.org/issue21574
        # "mitmproxy/data/image.ico",
    ]:
        with open(tutils.test_data.path(img), "rb") as f:
            viewname, lines = v(f.read())
            assert img.split(".")[-1].upper() in viewname

    assert v(b"flibble") == ('Unknown Image', [[('header', 'Image Format: '), ('text', 'unknown')]])
