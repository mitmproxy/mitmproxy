import cStringIO

from libpathod import language
from libpathod.language import http2, base
import netlib
import tutils


def parse_request(s):
    return language.parse_pathoc(s, True).next()


class TestRequest:
    def test_nonascii(self):
        tutils.raises("ascii", parse_request, "get:\xf0")

    def test_err(self):
        tutils.raises(language.ParseException, parse_request, 'GET')

    def test_simple(self):
        r = parse_request('GET:"/foo"')
        assert r.method.string() == "GET"
        assert r.path.string() == "/foo"
        r = parse_request('GET:/foo')
        assert r.path.string() == "/foo"

    def test_multiple(self):
        r = list(language.parse_pathoc("GET:/ PUT:/"))
        assert r[0].method.string() == "GET"
        assert r[1].method.string() == "PUT"
        assert len(r) == 2

        l = """
            GET
            "/foo"

            PUT

            "/foo



            bar"
        """
        r = list(language.parse_pathoc(l, True))
        assert len(r) == 2
        assert r[0].method.string() == "GET"
        assert r[1].method.string() == "PUT"

        l = """
            get:"http://localhost:9999/p/200"
            get:"http://localhost:9999/p/200"
        """
        r = list(language.parse_pathoc(l, True))
        assert len(r) == 2
        assert r[0].method.string() == "GET"
        assert r[1].method.string() == "GET"

    def test_render(self):
        s = cStringIO.StringIO()
        r = parse_request("GET:'/foo'")
        assert language.serve(
            r,
            s,
            language.Settings(
                request_host = "foo.com",
                protocol = netlib.http2.HTTP2Protocol(None)
            )
        )

    def test_spec(self):
        def rt(s):
            s = parse_request(s).spec()
            assert parse_request(s).spec() == s
        rt("get:/foo")
