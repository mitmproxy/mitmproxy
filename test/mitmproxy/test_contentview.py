import mock
from mitmproxy.exceptions import ContentViewException
from netlib.http import Headers
from netlib.http import url
from netlib import multidict

import mitmproxy.contentviews as cv
from . import tutils
import netlib.tutils

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
            b"foo",
            headers=Headers()
        )
        assert f[0] == "Raw"

        f = v(
            b"<html></html>",
            headers=Headers(content_type="text/html")
        )
        assert f[0] == "HTML"

        f = v(
            b"foo",
            headers=Headers(content_type="text/flibble")
        )
        assert f[0] == "Raw"

        f = v(
            b"<xml></xml>",
            headers=Headers(content_type="text/flibble")
        )
        assert f[0].startswith("XML")

        f = v(
            b"",
            headers=Headers()
        )
        assert f[0] == "No content"

        f = v(
            b"",
            headers=Headers(),
            query=multidict.MultiDict([("foo", "bar")]),
        )
        assert f[0] == "Query"

    def test_view_urlencoded(self):
        d = url.encode([("one", "two"), ("three", "four")]).encode()
        v = cv.ViewURLEncoded()
        assert v(d)
        d = url.encode([("adsfa", "")]).encode()
        v = cv.ViewURLEncoded()
        assert v(d)

    def test_view_html(self):
        v = cv.ViewHTML()
        s = b"<html><br><br></br><p>one</p></html>"
        assert v(s)

        s = b"gobbledygook"
        assert not v(s)

    def test_view_html_outline(self):
        v = cv.ViewHTMLOutline()
        s = b"<html><br><br></br><p>one</p></html>"
        assert v(s)
        assert v(b'\xfe')

    def test_view_json(self):
        cv.VIEW_CUTOFF = 100
        v = cv.ViewJSON()
        assert v(b"{}")
        assert not v(b"{")
        assert v(b"[1, 2, 3, 4, 5]")

    def test_view_xml(self):
        v = cv.ViewXML()
        assert v(b"<foo></foo>")
        assert not v(b"<foo>")
        s = b"""<?xml version="1.0" encoding="UTF-8"?>
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
        assert v(b"foo")

    def test_view_javascript(self):
        v = cv.ViewJavaScript()
        assert v(b"[1, 2, 3]")
        assert v(b"[1, 2, 3")
        assert v(b"function(a){[1, 2, 3]}")
        assert v(b"\xfe")  # invalid utf-8

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
        assert v(b"foo")

    def test_view_image(self):
        v = cv.ViewImage()
        p = tutils.test_data.path("data/image.png")
        assert v(open(p, "rb").read())

        p = tutils.test_data.path("data/image.gif")
        assert v(open(p, "rb").read())

        p = tutils.test_data.path("data/image-err1.jpg")
        assert v(open(p, "rb").read())

        p = tutils.test_data.path("data/image.ico")
        assert v(open(p, "rb").read())

        assert not v(b"flibble")

    def test_view_multipart(self):
        view = cv.ViewMultipart()
        v = b"""
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
        f = v(d, query=multidict.MultiDict([("foo", "bar")]))
        assert f[0] == "Query"
        assert [x for x in f[1]] == [[("header", "foo: "), ("text", "bar")]]

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


def test_get_content_view():
    desc, lines, err = cv.get_content_view(
        cv.get("Raw"),
        b"[1, 2, 3]",
    )
    assert "Raw" in desc
    assert list(lines)
    assert not err

    desc, lines, err = cv.get_content_view(
        cv.get("Auto"),
        b"[1, 2, 3]",
        headers=Headers(content_type="application/json")
    )
    assert desc == "JSON"

    desc, lines, err = cv.get_content_view(
        cv.get("JSON"),
        b"[1, 2",
    )
    assert "Couldn't parse" in desc

    with mock.patch("mitmproxy.contentviews.ViewAuto.__call__") as view_auto:
        view_auto.side_effect = ValueError

        desc, lines, err = cv.get_content_view(
            cv.get("Auto"),
            b"[1, 2",
        )
        assert err
        assert "Couldn't parse" in desc


def test_get_message_content_view():
    r = netlib.tutils.treq()
    desc, lines, err = cv.get_message_content_view(cv.get("Raw"), r)
    assert desc == "Raw"

    r.encode("gzip")
    desc, lines, err = cv.get_message_content_view(cv.get("Raw"), r)
    assert desc == "[decoded gzip] Raw"

    r.headers["content-encoding"] = "deflate"
    desc, lines, err = cv.get_message_content_view(cv.get("Raw"), r)
    assert desc == "[cannot decode] Raw"

    r.content = None
    desc, lines, err = cv.get_message_content_view(cv.get("Raw"), r)
    assert list(lines) == [[("error", "content missing")]]


if pyamf:
    def test_view_amf_request():
        v = cv.ViewAMF()

        p = tutils.test_data.path("data/amf01")
        assert v(open(p, "rb").read())

        p = tutils.test_data.path("data/amf02")
        assert v(open(p, "rb").read())

    def test_view_amf_response():
        v = cv.ViewAMF()
        p = tutils.test_data.path("data/amf03")
        assert v(open(p, "rb").read())

if cv.ViewProtobuf.is_available():
    def test_view_protobuf_request():
        v = cv.ViewProtobuf()

        p = tutils.test_data.path("data/protobuf01")
        content_type, output = v(open(p, "rb").read())
        assert content_type == "Protobuf"
        assert output.next()[0][1] == '1: "3bbc333c-e61c-433b-819a-0b9a8cc103b8"'


def test_get_by_shortcut():
    assert cv.get_by_shortcut("h")


def test_pretty_json():
    assert cv.pretty_json(b'{"foo": 1}')
    assert not cv.pretty_json(b"moo")
    assert cv.pretty_json(b'{"foo" : "\xe4\xb8\x96\xe7\x95\x8c"}')  # utf8 with chinese characters
    assert not cv.pretty_json(b'{"foo" : "\xFF"}')
