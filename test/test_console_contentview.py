import os
from nose.plugins.skip import SkipTest
if os.name == "nt":
    raise SkipTest("Skipped on Windows.")
import sys

from netlib import odict
import libmproxy.console.contentview as cv
from libmproxy import utils, flow, encoding
import tutils

try:
    import pyamf
except ImportError:
    pyamf = None

try:
    import cssutils
except:
    cssutils = None


class TestContentView:
    def test_trailer(self):
        txt = []
        cv.trailer(5, txt, 1000)
        assert not txt
        cv.trailer(cv.VIEW_CUTOFF + 10, txt, cv.VIEW_CUTOFF)
        assert txt

    def test_view_auto(self):
        v = cv.ViewAuto()
        f = v(
            odict.ODictCaseless(),
            "foo",
            1000
        )
        assert f[0] == "Raw"

        f = v(
            odict.ODictCaseless(
                [["content-type", "text/html"]],
            ),
            "<html></html>",
            1000
        )
        assert f[0] == "HTML"

        f = v(
            odict.ODictCaseless(
                [["content-type", "text/flibble"]],
            ),
            "foo",
            1000
        )
        assert f[0] == "Raw"

        f = v(
            odict.ODictCaseless(
                [["content-type", "text/flibble"]],
            ),
            "<xml></xml>",
            1000
        )
        assert f[0].startswith("XML")

    def test_view_urlencoded(self):
        d = utils.urlencode([("one", "two"), ("three", "four")])
        v = cv.ViewURLEncoded()
        assert v([], d, 100)
        d = utils.urlencode([("adsfa", "")])
        v = cv.ViewURLEncoded()
        assert v([], d, 100)

    def test_view_html(self):
        v = cv.ViewHTML()
        s = "<html><br><br></br><p>one</p></html>"
        assert v([], s, 1000)

        s = "gobbledygook"
        assert not v([], s, 1000)

    def test_view_html_outline(self):
        v = cv.ViewHTMLOutline()
        s = "<html><br><br></br><p>one</p></html>"
        assert v([], s, 1000)

    def test_view_json(self):
        cv.VIEW_CUTOFF = 100
        v = cv.ViewJSON()
        assert v([], "{}", 1000)
        assert not v([], "{", 1000)
        assert v([], "[" + ",".join(["0"] * cv.VIEW_CUTOFF) + "]", 1000)
        assert v([], "[1, 2, 3, 4, 5]", 5)

    def test_view_xml(self):
        v = cv.ViewXML()
        assert v([], "<foo></foo>", 1000)
        assert not v([], "<foo>", 1000)
        s = """<?xml version="1.0" encoding="UTF-8"?>
            <?xml-stylesheet title="XSL_formatting"?>
            <rss
                xmlns:media="http://search.yahoo.com/mrss/"
                xmlns:atom="http://www.w3.org/2005/Atom"
                version="2.0">
            </rss>
        """
        assert v([], s, 1000)

    def test_view_raw(self):
        v = cv.ViewRaw()
        assert v([], "foo", 1000)

    def test_view_javascript(self):
        v = cv.ViewJavaScript()
        assert v([], "[1, 2, 3]", 100)
        assert v([], "[1, 2, 3", 100)
        assert v([], "function(a){[1, 2, 3]}", 100)

    def test_view_css(self):
        v = cv.ViewCSS()

        with open(tutils.test_data.path('data/1.css'), 'r') as fp:
            fixture_1 = fp.read()

        result = v([], 'a', 100)

        if cssutils:
            assert len(result[1]) == 0
        else:
            assert len(result[1]) == 1

        result = v([], fixture_1, 100)

        if cssutils:
            assert len(result[1]) > 1
        else:
            assert len(result[1]) == 1

    def test_view_hex(self):
        v = cv.ViewHex()
        assert v([], "foo", 1000)

    def test_view_image(self):
        v = cv.ViewImage()
        p = tutils.test_data.path("data/image.png")
        assert v([], file(p, "rb").read(), sys.maxsize)

        p = tutils.test_data.path("data/image.gif")
        assert v([], file(p, "rb").read(), sys.maxsize)

        p = tutils.test_data.path("data/image-err1.jpg")
        assert v([], file(p, "rb").read(), sys.maxsize)

        p = tutils.test_data.path("data/image.ico")
        assert v([], file(p, "rb").read(), sys.maxsize)

        assert not v([], "flibble", sys.maxsize)

    def test_view_multipart(self):
        view = cv.ViewMultipart()
        v = """
--AaB03x
Content-Disposition: form-data; name="submit-name"

Larry
--AaB03x
        """.strip()
        h = odict.ODictCaseless(
            [("Content-Type", "multipart/form-data; boundary=AaB03x")]
        )
        assert view(h, v, 1000)

        h = odict.ODictCaseless()
        assert not view(h, v, 1000)

        h = odict.ODictCaseless(
            [("Content-Type", "multipart/form-data")]
        )
        assert not view(h, v, 1000)

        h = odict.ODictCaseless(
            [("Content-Type", "unparseable")]
        )
        assert not view(h, v, 1000)

    def test_get_content_view(self):
        r = cv.get_content_view(
            cv.get("Raw"),
            [["content-type", "application/json"]],
            "[1, 2, 3]",
            1000,
            False
        )
        assert "Raw" in r[0]

        r = cv.get_content_view(
            cv.get("Auto"),
            [["content-type", "application/json"]],
            "[1, 2, 3]",
            1000,
            False
        )
        assert r[0] == "JSON"

        r = cv.get_content_view(
            cv.get("Auto"),
            [["content-type", "application/json"]],
            "[1, 2",
            1000,
            False
        )
        assert "Raw" in r[0]

        r = cv.get_content_view(
            cv.get("AMF"),
            [],
            "[1, 2",
            1000,
            False
        )
        assert "Raw" in r[0]

        r = cv.get_content_view(
            cv.get("Auto"),
            [
                ["content-type", "application/json"],
                ["content-encoding", "gzip"]
            ],
            encoding.encode('gzip', "[1, 2, 3]"),
            1000,
            False
        )
        assert "decoded gzip" in r[0]
        assert "JSON" in r[0]

        r = cv.get_content_view(
            cv.get("XML"),
            [
                ["content-type", "application/json"],
                ["content-encoding", "gzip"]
            ],
            encoding.encode('gzip', "[1, 2, 3]"),
            1000,
            False
        )
        assert "decoded gzip" in r[0]
        assert "Raw" in r[0]


if pyamf:
    def test_view_amf_request():
        v = cv.ViewAMF()

        p = tutils.test_data.path("data/amf01")
        assert v([], file(p, "rb").read(), sys.maxsize)

        p = tutils.test_data.path("data/amf02")
        assert v([], file(p, "rb").read(), sys.maxsize)

    def test_view_amf_response():
        v = cv.ViewAMF()
        p = tutils.test_data.path("data/amf03")
        assert v([], file(p, "rb").read(), sys.maxsize)

if cv.ViewProtobuf.is_available():
    def test_view_protobuf_request():
        v = cv.ViewProtobuf()

        p = tutils.test_data.path("data/protobuf01")
        content_type, output = v([], file(p, "rb").read(), sys.maxsize)
        assert content_type == "Protobuf"
        assert output[0].text == '1: "3bbc333c-e61c-433b-819a-0b9a8cc103b8"'


def test_get_by_shortcut():
    assert cv.get_by_shortcut("h")
