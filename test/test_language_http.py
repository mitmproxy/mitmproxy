import cStringIO

from libpathod import language
from libpathod.language import http, base
import tutils


def parse_request(s):
    return language.parse_requests(s)[0]


def test_make_error_response():
    d = cStringIO.StringIO()
    s = http.make_error_response("foo")
    language.serve(s, d, {})


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
        r = parse_request('GET:@1k')
        assert len(r.path.string()) == 1024

    def test_multiple(self):
        r = language.parse_requests("GET:/ PUT:/")
        assert r[0].method.string() == "GET"
        assert r[1].method.string() == "PUT"
        assert len(r) == 2

        l = """
            GET
            "/foo"
            ir,@1

            PUT

            "/foo



            bar"

            ir,@1
        """
        r = language.parse_requests(l)
        assert len(r) == 2
        assert r[0].method.string() == "GET"
        assert r[1].method.string() == "PUT"

        l = """
            get:"http://localhost:9999/p/200":ir,@1
            get:"http://localhost:9999/p/200":ir,@2
        """
        r = language.parse_requests(l)
        assert len(r) == 2
        assert r[0].method.string() == "GET"
        assert r[1].method.string() == "GET"

    def test_pathodspec(self):
        l = "get:/p:s'200'"
        r = language.parse_requests(l)
        assert len(r) == 1
        assert len(r[0].tokens) == 3
        assert isinstance(r[0].tokens[2], base.PathodSpec)
        assert r[0].values({})

    def test_render(self):
        s = cStringIO.StringIO()
        r = parse_request("GET:'/foo'")
        assert language.serve(
            r,
            s,
            language.Settings(request_host = "foo.com")
        )

    def test_multiline(self):
        l = """
            GET
            "/foo"
            ir,@1
        """
        r = parse_request(l)
        assert r.method.string() == "GET"
        assert r.path.string() == "/foo"
        assert r.actions

        l = """
            GET

            "/foo



            bar"

            ir,@1
        """
        r = parse_request(l)
        assert r.method.string() == "GET"
        assert r.path.string().endswith("bar")
        assert r.actions

    def test_spec(self):
        def rt(s):
            s = parse_request(s).spec()
            assert parse_request(s).spec() == s
        rt("get:/foo")
        rt("get:/foo:da")

    def test_freeze(self):
        r = parse_request("GET:/:b@100").freeze(language.Settings())
        assert len(r.spec()) > 100

    def test_path_generator(self):
        r = parse_request("GET:@100").freeze(language.Settings())
        assert len(r.spec()) > 100

    def test_websocket(self):
        r = parse_request('ws:/path/')
        res = r.resolve(language.Settings())
        assert res.method.string().lower() == "get"
        assert res.tok(http.Path).value.val == "/path/"
        assert res.tok(http.Method).value.val.lower() == "get"
        assert http.get_header("Upgrade", res.headers).value.val == "websocket"

        r = parse_request('ws:put:/path/')
        res = r.resolve(language.Settings())
        assert r.method.string().lower() == "put"
        assert res.tok(http.Path).value.val == "/path/"
        assert res.tok(http.Method).value.val.lower() == "put"
        assert http.get_header("Upgrade", res.headers).value.val == "websocket"


class TestResponse:
    def dummy_response(self):
        return language.parse_response("400'msg'")

    def test_response(self):
        r = language.parse_response("400:m'msg'")
        assert r.code.string() == "400"
        assert r.reason.string() == "msg"

        r = language.parse_response("400:m'msg':b@100b")
        assert r.reason.string() == "msg"
        assert r.body.values({})
        assert str(r)

        r = language.parse_response("200")
        assert r.code.string() == "200"
        assert not r.reason
        assert "OK" in [i[:] for i in r.preamble({})]

    def test_render(self):
        s = cStringIO.StringIO()
        r = language.parse_response("400:m'msg'")
        assert language.serve(r, s, {})

        r = language.parse_response("400:p0,100:dr")
        assert "p0" in r.spec()
        s = r.preview_safe()
        assert "p0" not in s.spec()

    def test_raw(self):
        s = cStringIO.StringIO()
        r = language.parse_response("400:b'foo'")
        language.serve(r, s, {})
        v = s.getvalue()
        assert "Content-Length" in v

        s = cStringIO.StringIO()
        r = language.parse_response("400:b'foo':r")
        language.serve(r, s, {})
        v = s.getvalue()
        assert "Content-Length" not in v

    def test_length(self):
        def testlen(x):
            s = cStringIO.StringIO()
            language.serve(x, s, language.Settings())
            assert x.length(language.Settings()) == len(s.getvalue())
        testlen(language.parse_response("400:m'msg':r"))
        testlen(language.parse_response("400:m'msg':h'foo'='bar':r"))
        testlen(language.parse_response("400:m'msg':h'foo'='bar':b@100b:r"))

    def test_maximum_length(self):
        def testlen(x):
            s = cStringIO.StringIO()
            m = x.maximum_length({})
            language.serve(x, s, {})
            assert m >= len(s.getvalue())

        r = language.parse_response("400:m'msg':b@100:d0")
        testlen(r)

        r = language.parse_response("400:m'msg':b@100:d0:i0,'foo'")
        testlen(r)

        r = language.parse_response("400:m'msg':b@100:d0:i0,'foo'")
        testlen(r)

    def test_parse_err(self):
        tutils.raises(
            language.ParseException, language.parse_response, "400:msg,b:"
        )
        try:
            language.parse_response("400'msg':b:")
        except language.ParseException, v:
            assert v.marked()
            assert str(v)

    def test_nonascii(self):
        tutils.raises("ascii", language.parse_response, "foo:b\xf0")

    def test_parse_header(self):
        r = language.parse_response('400:h"foo"="bar"')
        assert http.get_header("foo", r.headers)

    def test_parse_pause_before(self):
        r = language.parse_response("400:p0,10")
        assert r.actions[0].spec() == "p0,10"

    def test_parse_pause_after(self):
        r = language.parse_response("400:pa,10")
        assert r.actions[0].spec() == "pa,10"

    def test_parse_pause_random(self):
        r = language.parse_response("400:pr,10")
        assert r.actions[0].spec() == "pr,10"

    def test_parse_stress(self):
        # While larger values are known to work on linux, len() technically
        # returns an int and a python 2.7 int on windows has 32bit precision.
        # Therefore, we should keep the body length < 2147483647 bytes in our
        # tests.
        r = language.parse_response("400:b@1g")
        assert r.length({})

    def test_spec(self):
        def rt(s):
            s = language.parse_response(s).spec()
            assert language.parse_response(s).spec() == s
        rt("400:b@100g")
        rt("400")
        rt("400:da")

    def test_websockets(self):
        r = language.parse_response("ws")
        tutils.raises("no websocket key", r.resolve, language.Settings())
        res = r.resolve(language.Settings(websocket_key="foo"))
        assert res.code.string() == "101"
