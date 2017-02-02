import io

from mitmproxy.contentviews.image import image_parser
from mitmproxy.test import tutils

class TestPngParser:
    def test_png_parser(self):
        img = "mitmproxy/data/image.png"
        with open(tutils.test_data.path(img), "rb") as f:
            parts = image_parser.parse_png(io.BytesIO(f.read()))
            assert parts
            assert tuple(['Size', '174 x 174 px']) in parts
            assert tuple(["Format", "Portable network graphics"]) in parts

    def test_textual_data(self):
        img = "mitmproxy/data/png_parser/ct1n0g04.png"
        with open(tutils.test_data.path(img), "rb") as f:
            parts = image_parser.parse_png(io.BytesIO(f.read()))
            assert parts
            expected = [
                ('Title', 'PngSuite'),
                ('Author', 'Willem A.J. van Schaik\n(willem@schaik.com)'),
                ('Copyright', 'Copyright Willem van Schaik, Singapore 1995-96'),
                ('Description', 'A compilation of a set of images created to test the\nvarious color-types of the PNG format. Included are\nblack&white, color, paletted, with alpha channel, with\ntransparency formats. All bit-depths allowed according\nto the spec are present.'),
                ('Software', 'Created on a NeXTstation color using "pnmtopng".'),
                ('Disclaimer', 'Freeware.')
            ]
            for data in expected:
                assert data in parts

    def test_no_textual_data(self):
        img = "mitmproxy/data/png_parser/ct0n0g04.png"
        with open(tutils.test_data.path(img), "rb") as f:
            parts = image_parser.parse_png(io.BytesIO(f.read()))
            assert parts
            metadata = [
                ('Format', 'Portable network graphics'),
                ('Size', '32 x 32 px'),
                ('gamma', '1.0')
                ]
            parts = [data for data in parts if data not in metadata]
            assert not parts

    def test_gamma(self):
        img = "mitmproxy/data/png_parser/g07n0g16.png"
        with open(tutils.test_data.path(img), "rb") as f:
            parts = image_parser.parse_png(io.BytesIO(f.read()))
            assert parts
            assert ('gamma', '0.7') in parts

    def test_gamma(self):
        img = "mitmproxy/data/png_parser/aspect.png"
        with open(tutils.test_data.path(img), "rb") as f:
            parts = image_parser.parse_png(io.BytesIO(f.read()))
            assert parts
            assert ('aspect', '72 x 72') in parts
