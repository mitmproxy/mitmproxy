import sys
import libmproxy.console.contentview as cv
from libmproxy import utils, flow, encoding
import tutils

class TestContentView:
    def test_trailer(self):
        txt = []
        cv.trailer(5, txt, 1000)
        assert not txt
        cv.trailer(cv.VIEW_CUTOFF + 10, txt, cv.VIEW_CUTOFF)
        assert txt

    def test_get_view_func(self):
        f = cv.get_view_func(
                cv.get("Hex"),
                flow.ODictCaseless(),
                "foo"
              )
        assert f.name == "Hex"

        f = cv.get_view_func(
                cv.get("Auto"),
                flow.ODictCaseless(),
                "foo"
              )
        assert f.name == "Raw"

        f = cv.get_view_func(
                cv.get("Auto"),
                flow.ODictCaseless(
                    [["content-type", "text/html"]],
                ),
                "foo"
              )
        assert f.name == "HTML"

        f = cv.get_view_func(
                cv.get("Auto"),
                flow.ODictCaseless(
                    [["content-type", "text/flibble"]],
                ),
                "foo"
              )
        assert f.name == "Raw"

        f = cv.get_view_func(
                cv.get("Auto"),
                flow.ODictCaseless(
                    [["content-type", "text/flibble"]],
                ),
                "<xml></xml>"
              )
        assert f.name == "XML" 

        try:
            import pyamf

            f = cv.get_view_func(
                    cv.get("Auto"),
                    flow.ODictCaseless(
                        [["content-type", "application/x-amf"]],
                    ),
                    ""
                  )
            assert f.name == "AMF"
        except ImportError:
            pass

    def test_view_urlencoded(self):
        d = utils.urlencode([("one", "two"), ("three", "four")])
        v = cv.ViewURLEncoded()
        assert v([], d, 100)
        assert not v([], "foo", 100)

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
        assert v([], "[" + ",".join(["0"]*cv.VIEW_CUTOFF) + "]", 1000)
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

    def test_view_hex(self):
        v = cv.ViewHex()
        assert v([], "foo", 1000)

    def test_view_image(self):
        v = cv.ViewImage()
        p = tutils.test_data.path("data/image.png")
        assert v([], file(p).read(), sys.maxint)

        p = tutils.test_data.path("data/image.gif")
        assert v([], file(p).read(), sys.maxint)

        p = tutils.test_data.path("data/image-err1.jpg")
        assert v([], file(p).read(), sys.maxint)

        p = tutils.test_data.path("data/image.ico")
        assert v([], file(p).read(), sys.maxint)

        assert not v([], "flibble", sys.maxint)

    def test_view_amf(self):
        try:
            import pyamf
            v = cv.ViewAMF()
            p = tutils.test_data.path("data/test.amf")
            assert v([], file(p).read(), sys.maxint)
        except ImportError:
            pass

    def test_view_multipart(self):
        view = cv.ViewMultipart()
        v = """
--AaB03x
Content-Disposition: form-data; name="submit-name"

Larry
--AaB03x
        """.strip()
        h = flow.ODictCaseless(
            [("Content-Type", "multipart/form-data; boundary=AaB03x")]
        )
        assert view(h, v, 1000)

        h = flow.ODictCaseless()
        assert not view(h, v, 1000)

        h = flow.ODictCaseless(
            [("Content-Type", "multipart/form-data")]
        )
        assert not view(h, v, 1000)

        h = flow.ODictCaseless(
            [("Content-Type", "unparseable")]
        )
        assert not view(h, v, 1000)

    def test_get_content_view(self):
        r = cv.get_content_view(
                cv.get("Raw"),
                [["content-type", "application/json"]],
                "[1, 2, 3]",
                1000
              )
        assert "Raw" in r[0]

        r = cv.get_content_view(
                cv.get("Auto"),
                [["content-type", "application/json"]],
                "[1, 2, 3]",
                1000
              )
        assert r[0] == "JSON"

        r = cv.get_content_view(
                cv.get("Auto"),
                [["content-type", "application/json"]],
                "[1, 2",
                1000
              )
        assert "Raw" in r[0]

        r = cv.get_content_view(
                cv.get("Auto"),
                [
                    ["content-type", "application/json"],
                    ["content-encoding", "gzip"]
                ],
                encoding.encode('gzip', "[1, 2, 3]"),
                1000
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
                1000
              )
        assert "decoded gzip" in r[0]
        assert "Raw" in r[0]

