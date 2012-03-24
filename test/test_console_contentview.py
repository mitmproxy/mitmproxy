import libpry
import libmproxy.console.contentview as cv
from libmproxy import utils, flow, encoding

class uContentView(libpry.AutoTree):
    def test_trailer(self):
        txt = []
        cv.trailer(5, txt)
        assert not txt
        cv.trailer(cv.VIEW_CUTOFF + 10, txt)
        assert txt
        
    def test_get_view_func(self):
        f = cv.get_view_func(
                cv.VIEW_CONTENT_HEX,
                cv.VIEW_CONTENT_PRETTY_TYPE_AUTO,
                flow.ODictCaseless(),
                "foo"
              )
        assert f is cv.view_hex

        f = cv.get_view_func(
                cv.VIEW_CONTENT_RAW,
                cv.VIEW_CONTENT_PRETTY_TYPE_AUTO,
                flow.ODictCaseless(),
                "foo"
              )
        assert f is cv.view_raw

        f = cv.get_view_func(
                cv.VIEW_CONTENT_PRETTY,
                cv.VIEW_CONTENT_PRETTY_TYPE_AUTO,
                flow.ODictCaseless(
                    [["content-type", "text/html"]],
                ),
                "foo"
              )
        assert f is cv.view_xmlish

        f = cv.get_view_func(
                cv.VIEW_CONTENT_PRETTY,
                cv.VIEW_CONTENT_PRETTY_TYPE_AUTO,
                flow.ODictCaseless(
                    [["content-type", "text/flibble"]],
                ),
                "foo"
              )
        assert f is cv.view_raw

        f = cv.get_view_func(
                cv.VIEW_CONTENT_PRETTY,
                cv.VIEW_CONTENT_PRETTY_TYPE_AUTO,
                flow.ODictCaseless(
                    [["content-type", "text/flibble"]],
                ),
                "<xml></xml>"
              )
        assert f is cv.view_xmlish

    def test_view_urlencoded(self):
        d = utils.urlencode([("one", "two"), ("three", "four")])
        assert cv.view_urlencoded([], d)
        assert not cv.view_urlencoded([], "foo")

    def test_view_json(self):
        cv.VIEW_CUTOFF = 100
        assert cv.view_json([], "{}")
        assert not cv.view_urlencoded([], "{")
        assert cv.view_json([], "[" + ",".join(["0"]*cv.VIEW_CUTOFF) + "]")

    def test_view_xmlish(self):
        assert cv.view_xmlish([], "<foo></foo>")
        assert cv.view_xmlish([], "<foo>")

    def test_view_raw(self):
        assert cv.view_raw([], "foo")

    def test_view_raw(self):
        assert cv.view_hex([], "foo")

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
        assert cv.view_multipart(h, v)

        h = flow.ODictCaseless()
        assert not cv.view_multipart(h, v)

        h = flow.ODictCaseless(
            [("Content-Type", "multipart/form-data")]
        )
        assert not cv.view_multipart(h, v)

        h = flow.ODictCaseless(
            [("Content-Type", "unparseable")]
        )
        assert not cv.view_multipart(h, v)

    def test_get_content_view(self):
        r = cv.get_content_view(
                cv.VIEW_CONTENT_RAW,
                cv.VIEW_CONTENT_PRETTY_TYPE_AUTO,
                [["content-type", "application/json"]],
                "[1, 2, 3]"
              )
        assert r[0] == "Raw"

        r = cv.get_content_view(
                cv.VIEW_CONTENT_PRETTY,
                cv.VIEW_CONTENT_PRETTY_TYPE_AUTO,
                [["content-type", "application/json"]],
                "[1, 2, 3]"
              )
        assert r[0] == "JSON"


        r = cv.get_content_view(
                cv.VIEW_CONTENT_PRETTY,
                cv.VIEW_CONTENT_PRETTY_TYPE_AUTO,
                [["content-type", "application/json"]],
                "[1, 2"
              )
        assert r[0] == "Raw"

        r = cv.get_content_view(
                cv.VIEW_CONTENT_PRETTY,
                cv.VIEW_CONTENT_PRETTY_TYPE_AUTO,
                [
                    ["content-type", "application/json"],
                    ["content-encoding", "gzip"]
                ],
                encoding.encode('gzip', "[1, 2, 3]")
              )
        assert "decoded gzip" in r[0]
        assert "JSON" in r[0]


        r = cv.get_content_view(
                cv.VIEW_CONTENT_PRETTY,
                cv.VIEW_CONTENT_PRETTY_TYPE_XML,
                [
                    ["content-type", "application/json"],
                    ["content-encoding", "gzip"]
                ],
                encoding.encode('gzip', "[1, 2, 3]")
              )
        assert "decoded gzip" in r[0]
        assert "forced" in r[0]


tests = [
    uContentView()
]
