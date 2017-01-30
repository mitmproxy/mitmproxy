import io

from mitmproxy.contentviews.image import image_parser
from mitmproxy.test import tutils

def test_png_parser():
    img = "mitmproxy/data/image.png"
    with open(tutils.test_data.path(img), "rb") as f:
        fmt, parts = image_parser.get_png(io.BytesIO(f.read()))
        assert fmt == "PNG"
        assert parts
        assert parts["width"] == 174
        assert parts["height"] == 174
        assert parts["format"] == "Portable network graphics"
