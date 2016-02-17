from mitmproxy.exceptions import ContentViewException
from netlib.http import Headers
from netlib.odict import ODict
import netlib.utils
from netlib import encoding

import mitmproxy.contentviews as cv
from . import tutils

try:
    import pyamf
except ImportError:
    pyamf = None

try:
    import cssutils
except:
    cssutils = None


class TestContentView:

    def test_view_auto(self):
        v = cv.ViewAuto()
        f = v(
            "foo",
            headers=Headers()
        )
        assert f[0] == "Raw"

        f = v(
            "<html></html>",
            headers=Headers(content_type="text/html")
        )
        assert f[0] == "HTML"

        f = v(
            "foo",
            headers=Headers(content_type="text/flibble")
        )
        assert f[0] == "Raw"

        f = v(
            "<xml></xml>",
            headers=Headers(content_type="text/flibble")
        )
        assert f[0].startswith("XML")

        f = v(
            "",
            headers=Headers()
        )
        assert f[0] == "No content"

        f = v(
            "",
            headers=Headers(),
            query=ODict([("foo", "bar")]),
        )
        assert f[0] == "Query"

    def test_view_urlencoded(self):
        d = netlib.utils.urlencode([("one", "two"), ("three", "four")])
        v = cv.ViewURLEncoded()
        assert v(d)
        d = netlib.utils.urlencode([("adsfa", "")])
        v = cv.ViewURLEncoded()
        assert v(d)

    def test_view_html(self):
        v = cv.ViewHTML()
        s = "<html><br><br></br><p>one</p></html>"
        assert v(s)

        s = "gobbledygook"
        assert not v(s)

    def test_view_html_outline(self):
        v = cv.ViewHTMLOutline()
        s = "<html><br><br></br><p>one</p></html>"
        assert v(s)

    def test_view_json(self):
        cv.VIEW_CUTOFF = 100
        v = cv.ViewJSON()
        assert v("{}")
        assert not v("{")
        assert v("[1, 2, 3, 4, 5]")

    def test_view_xml(self):
        v = cv.ViewXML()
        assert v("<foo></foo>")
        assert not v("<foo>")
        s = """<?xml version="1.0" encoding="UTF-8"?>
            <?xml-stylesheet title="XSL_formatting"?>
            <rss
                xmlns:media="http://search.yahoo.com/mrss/"
                xmlns:atom="http://www.w3.org/2005/Atom"
                version="2.0">
            </rss>
        """
        assert v(s)

    def test_view_raw(self):
        v = cv.ViewRaw()
        assert v("foo")

    def test_view_javascript(self):
        v = cv.ViewJavaScript()
        assert v("[1, 2, 3]")
        assert v("[1, 2, 3")
        assert v("function(a){[1, 2, 3]}")

    def test_view_css(self):
        v = cv.ViewCSS()

        with open(tutils.test_data.path('data/1.css'), 'r') as fp:
            fixture_1 = fp.read()

        result = v('a')

        if cssutils:
            assert len(list(result[1])) == 0
        else:
            assert len(list(result[1])) == 1

        result = v(fixture_1)

        if cssutils:
            assert len(list(result[1])) > 1
        else:
            assert len(list(result[1])) == 1

    def test_view_hex(self):
        v = cv.ViewHex()
        assert v("foo")

    def test_view_image(self):
        v = cv.ViewImage()
        p = tutils.test_data.path("data/image.png")
        assert v(file(p, "rb").read())

        p = tutils.test_data.path("data/image.gif")
        assert v(file(p, "rb").read())

        p = tutils.test_data.path("data/image-err1.jpg")
        assert v(file(p, "rb").read())

        p = tutils.test_data.path("data/image.ico")
        assert v(file(p, "rb").read())

        assert not v("flibble")

    def test_view_multipart(self):
        view = cv.ViewMultipart()
        v = """
--AaB03x
Content-Disposition: form-data; name="submit-name"

Larry
--AaB03x
        """.strip()
        h = Headers(content_type="multipart/form-data; boundary=AaB03x")
        assert view(v, headers=h)

        h = Headers()
        assert not view(v, headers=h)

        h = Headers(content_type="multipart/form-data")
        assert not view(v, headers=h)

        h = Headers(content_type="unparseable")
        assert not view(v, headers=h)

    def test_view_query(self):
        d = ""
        v = cv.ViewQuery()
        f = v(d, query=ODict([("foo", "bar")]))
        assert f[0] == "Query"
        assert [x for x in f[1]] == [[("header", "foo: "), ("text", "bar")]]

    def test_get_content_view(self):
        r = cv.get_content_view(
            cv.get("Raw"),
            "[1, 2, 3]",
            headers=Headers(content_type="application/json")
        )
        assert "Raw" in r[0]

        r = cv.get_content_view(
            cv.get("Auto"),
            "[1, 2, 3]",
            headers=Headers(content_type="application/json")
        )
        assert r[0] == "JSON"

        r = cv.get_content_view(
            cv.get("Auto"),
            "[1, 2",
            headers=Headers(content_type="application/json")
        )
        assert "Raw" in r[0]

        tutils.raises(
            ContentViewException,
            cv.get_content_view,
            cv.get("AMF"),
            "[1, 2",
            headers=Headers()
        )

        r = cv.get_content_view(
            cv.get("Auto"),
            encoding.encode('gzip', "[1, 2, 3]"),
            headers=Headers(
                content_type="application/json",
                content_encoding="gzip"
            )
        )
        assert "decoded gzip" in r[0]
        assert "JSON" in r[0]

        r = cv.get_content_view(
            cv.get("XML"),
            encoding.encode('gzip', "[1, 2, 3]"),
            headers=Headers(
                content_type="application/json",
                content_encoding="gzip"
            )
        )
        assert "decoded gzip" in r[0]
        assert "Raw" in r[0]

    def test_add_cv(self):
        class TestContentView(cv.View):
            name = "test"
            prompt = ("t", "test")

        tcv = TestContentView()
        cv.add(tcv)

        # repeated addition causes exception
        tutils.raises(
            ContentViewException,
            cv.add,
            tcv
        )


if pyamf:
    def test_view_amf_request():
        v = cv.ViewAMF()

        p = tutils.test_data.path("data/amf01")
        assert v(file(p, "rb").read())

        p = tutils.test_data.path("data/amf02")
        assert v(file(p, "rb").read())

    def test_view_amf_response():
        v = cv.ViewAMF()
        p = tutils.test_data.path("data/amf03")
        assert v(file(p, "rb").read())

if cv.ViewProtobuf.is_available():
    def test_view_protobuf_request():
        v = cv.ViewProtobuf()

        p = tutils.test_data.path("data/protobuf01")
        content_type, output = v(file(p, "rb").read())
        assert content_type == "Protobuf"
        assert output.next()[0][1] == '1: "3bbc333c-e61c-433b-819a-0b9a8cc103b8"'


def test_get_by_shortcut():
    assert cv.get_by_shortcut("h")
