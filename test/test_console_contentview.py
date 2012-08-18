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
                cv.VIEW_HEX,
                flow.ODictCaseless(),
                "foo"
              )
        assert f is cv.view_hex

        f = cv.get_view_func(
                cv.VIEW_AUTO,
                flow.ODictCaseless(),
                "foo"
              )
        assert f is cv.view_raw

        f = cv.get_view_func(
                cv.VIEW_AUTO,
                flow.ODictCaseless(
                    [["content-type", "text/html"]],
                ),
                "foo"
              )
        assert f is cv.view_html

        f = cv.get_view_func(
                cv.VIEW_AUTO,
                flow.ODictCaseless(
                    [["content-type", "text/flibble"]],
                ),
                "foo"
              )
        assert f is cv.view_raw

        f = cv.get_view_func(
                cv.VIEW_AUTO,
                flow.ODictCaseless(
                    [["content-type", "text/flibble"]],
                ),
                "<xml></xml>"
              )
        assert f is cv.view_xml

        try:
            import pyamf

            f = cv.get_view_func(
                    cv.VIEW_AUTO,
                    flow.ODictCaseless(
                        [["content-type", "application/x-amf"]],
                    ),
                    ""
                  )
            assert f is cv.view_amf
        except ImportError:
            pass

    def test_view_urlencoded(self):
        d = utils.urlencode([("one", "two"), ("three", "four")])
        assert cv.view_urlencoded([], d, 100)
        assert not cv.view_urlencoded([], "foo", 100)

    def test_view_html(self):
        s = "<html><br><br></br><p>one</p></html>"
        assert cv.view_html([], s, 1000)

        s = "gobbledygook"
        assert not cv.view_html([], s, 1000)

    def test_view_json(self):
        cv.VIEW_CUTOFF = 100
        assert cv.view_json([], "{}", 1000)
        assert not cv.view_json([], "{", 1000)
        assert cv.view_json([], "[" + ",".join(["0"]*cv.VIEW_CUTOFF) + "]", 1000)
        assert cv.view_json([], "[1, 2, 3, 4, 5]", 5)

    def test_view_xml(self):
        assert cv.view_xml([], "<foo></foo>", 1000)
        assert not cv.view_xml([], "<foo>", 1000)
        s = """<?xml version="1.0" encoding="UTF-8"?>
            <?xml-stylesheet title="XSL_formatting"?>
            <rss
                xmlns:media="http://search.yahoo.com/mrss/"
                xmlns:atom="http://www.w3.org/2005/Atom"
                version="2.0">
            </rss>
        """
        assert cv.view_xml([], s, 1000)

    def test_view_raw(self):
        assert cv.view_raw([], "foo", 1000)

    def test_view_javascript(self):
        assert cv.view_javascript([], "[1, 2, 3]", 100)
        assert cv.view_javascript([], "[1, 2, 3", 100)
        assert cv.view_javascript([], "function(a){[1, 2, 3]}", 100)

    def test_view_hex(self):
        assert cv.view_hex([], "foo", 1000)

    def test_view_image(self):
        p = tutils.test_data.path("data/image.png")
        assert cv.view_image([], file(p).read(), sys.maxint)

        p = tutils.test_data.path("data/image.gif")
        assert cv.view_image([], file(p).read(), sys.maxint)

        p = tutils.test_data.path("data/image-err1.jpg")
        assert cv.view_image([], file(p).read(), sys.maxint)

        p = tutils.test_data.path("data/image.ico")
        assert cv.view_image([], file(p).read(), sys.maxint)

        assert not cv.view_image([], "flibble", sys.maxint)

    def test_view_amf(self):
        try:
            import pyamf

            p = tutils.test_data.path("data/test.amf")
            assert cv.view_amf([], file(p).read(), sys.maxint)
        except ImportError:
            pass

    def test_view_multipart(self):
        v = """
--AaB03x
Content-Disposition: form-data; name="submit-name"

Larry
--AaB03x
        """.strip()
        h = flow.ODictCaseless(
            [("Content-Type", "multipart/form-data; boundary=AaB03x")]
        )
        assert cv.view_multipart(h, v, 1000)

        h = flow.ODictCaseless()
        assert not cv.view_multipart(h, v, 1000)

        h = flow.ODictCaseless(
            [("Content-Type", "multipart/form-data")]
        )
        assert not cv.view_multipart(h, v, 1000)

        h = flow.ODictCaseless(
            [("Content-Type", "unparseable")]
        )
        assert not cv.view_multipart(h, v, 1000)

    def test_get_content_view(self):
        r = cv.get_content_view(
                cv.VIEW_RAW,
                [["content-type", "application/json"]],
                "[1, 2, 3]",
                1000
              )
        assert "Raw" in r[0]

        r = cv.get_content_view(
                cv.VIEW_AUTO,
                [["content-type", "application/json"]],
                "[1, 2, 3]",
                1000
              )
        assert r[0] == "JSON"

        r = cv.get_content_view(
                cv.VIEW_AUTO,
                [["content-type", "application/json"]],
                "[1, 2",
                1000
              )
        assert "Raw" in r[0]

        r = cv.get_content_view(
                cv.VIEW_AUTO,
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
                cv.VIEW_XML,
                [
                    ["content-type", "application/json"],
                    ["content-encoding", "gzip"]
                ],
                encoding.encode('gzip', "[1, 2, 3]"),
                1000
              )
        assert "decoded gzip" in r[0]
        assert "Raw" in r[0]

