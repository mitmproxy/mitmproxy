from six.moves import cStringIO as StringIO
from pathod import language
from pathod.language import http, base
import tutils


def parse_request(s):
    return language.parse_pathoc(s).next()


def test_make_error_response():
    d = StringIO()
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
        r = list(language.parse_pathoc("GET:/ PUT:/"))
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
        r = list(language.parse_pathoc(l))
        assert len(r) == 2
        assert r[0].method.string() == "GET"
        assert r[1].method.string() == "PUT"

        l = """
            get:"http://localhost:9999/p/200":ir,@1
            get:"http://localhost:9999/p/200":ir,@2
        """
        r = list(language.parse_pathoc(l))
        assert len(r) == 2
        assert r[0].method.string() == "GET"
        assert r[1].method.string() == "GET"

    def test_nested_response(self):
        l = "get:/p:s'200'"
        r = list(language.parse_pathoc(l))
        assert len(r) == 1
        assert len(r[0].tokens) == 3
        assert isinstance(r[0].tokens[2], http.NestedResponse)
        assert r[0].values({})

    def test_render(self):
        s = StringIO()
        r = parse_request("GET:'/foo'")
        assert language.serve(
            r,
            s,
            language.Settings(request_host="foo.com")
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
        return language.parse_pathod("400'msg'").next()

    def test_response(self):
        r = language.parse_pathod("400:m'msg'").next()
        assert r.status_code.string() == "400"
        assert r.reason.string() == "msg"

        r = language.parse_pathod("400:m'msg':b@100b").next()
        assert r.reason.string() == "msg"
        assert r.body.values({})
        assert str(r)

        r = language.parse_pathod("200").next()
        assert r.status_code.string() == "200"
        assert not r.reason
        assert "OK" in [i[:] for i in r.preamble({})]

    def test_render(self):
        s = StringIO()
        r = language.parse_pathod("400:m'msg'").next()
        assert language.serve(r, s, {})

        r = language.parse_pathod("400:p0,100:dr").next()
        assert "p0" in r.spec()
        s = r.preview_safe()
        assert "p0" not in s.spec()

    def test_raw(self):
        s = StringIO()
        r = language.parse_pathod("400:b'foo'").next()
        language.serve(r, s, {})
        v = s.getvalue()
        assert "Content-Length" in v

        s = StringIO()
        r = language.parse_pathod("400:b'foo':r").next()
        language.serve(r, s, {})
        v = s.getvalue()
        assert "Content-Length" not in v

    def test_length(self):
        def testlen(x):
            s = StringIO()
            x = x.next()
            language.serve(x, s, language.Settings())
            assert x.length(language.Settings()) == len(s.getvalue())
        testlen(language.parse_pathod("400:m'msg':r"))
        testlen(language.parse_pathod("400:m'msg':h'foo'='bar':r"))
        testlen(language.parse_pathod("400:m'msg':h'foo'='bar':b@100b:r"))

    def test_maximum_length(self):
        def testlen(x):
            x = x.next()
            s = StringIO()
            m = x.maximum_length({})
            language.serve(x, s, {})
            assert m >= len(s.getvalue())

        r = language.parse_pathod("400:m'msg':b@100:d0")
        testlen(r)

        r = language.parse_pathod("400:m'msg':b@100:d0:i0,'foo'")
        testlen(r)

        r = language.parse_pathod("400:m'msg':b@100:d0:i0,'foo'")
        testlen(r)

    def test_parse_err(self):
        tutils.raises(
            language.ParseException, language.parse_pathod, "400:msg,b:"
        )
        try:
            language.parse_pathod("400'msg':b:")
        except language.ParseException as v:
            assert v.marked()
            assert str(v)

    def test_nonascii(self):
        tutils.raises("ascii", language.parse_pathod, "foo:b\xf0")

    def test_parse_header(self):
        r = language.parse_pathod('400:h"foo"="bar"').next()
        assert http.get_header("foo", r.headers)

    def test_parse_pause_before(self):
        r = language.parse_pathod("400:p0,10").next()
        assert r.actions[0].spec() == "p0,10"

    def test_parse_pause_after(self):
        r = language.parse_pathod("400:pa,10").next()
        assert r.actions[0].spec() == "pa,10"

    def test_parse_pause_random(self):
        r = language.parse_pathod("400:pr,10").next()
        assert r.actions[0].spec() == "pr,10"

    def test_parse_stress(self):
        # While larger values are known to work on linux, len() technically
        # returns an int and a python 2.7 int on windows has 32bit precision.
        # Therefore, we should keep the body length < 2147483647 bytes in our
        # tests.
        r = language.parse_pathod("400:b@1g").next()
        assert r.length({})

    def test_spec(self):
        def rt(s):
            s = language.parse_pathod(s).next().spec()
            assert language.parse_pathod(s).next().spec() == s
        rt("400:b@100g")
        rt("400")
        rt("400:da")

    def test_websockets(self):
        r = language.parse_pathod("ws").next()
        tutils.raises("no websocket key", r.resolve, language.Settings())
        res = r.resolve(language.Settings(websocket_key="foo"))
        assert res.status_code.string() == "101"


def test_ctype_shortcut():
    e = http.ShortcutContentType.expr()
    v = e.parseString("c'foo'")[0]
    assert v.key.val == "Content-Type"
    assert v.value.val == "foo"

    s = v.spec()
    assert s == e.parseString(s)[0].spec()

    e = http.ShortcutContentType.expr()
    v = e.parseString("c@100")[0]
    v2 = v.freeze({})
    v3 = v2.freeze({})
    assert v2.value.val == v3.value.val


def test_location_shortcut():
    e = http.ShortcutLocation.expr()
    v = e.parseString("l'foo'")[0]
    assert v.key.val == "Location"
    assert v.value.val == "foo"

    s = v.spec()
    assert s == e.parseString(s)[0].spec()

    e = http.ShortcutLocation.expr()
    v = e.parseString("l@100")[0]
    v2 = v.freeze({})
    v3 = v2.freeze({})
    assert v2.value.val == v3.value.val


def test_shortcuts():
    assert language.parse_pathod(
        "400:c'foo'").next().headers[0].key.val == "Content-Type"
    assert language.parse_pathod(
        "400:l'foo'").next().headers[0].key.val == "Location"

    assert "Android" in tutils.render(parse_request("get:/:ua"))
    assert "User-Agent" in tutils.render(parse_request("get:/:ua"))


def test_user_agent():
    e = http.ShortcutUserAgent.expr()
    v = e.parseString("ua")[0]
    assert "Android" in v.string()

    e = http.ShortcutUserAgent.expr()
    v = e.parseString("u'a'")[0]
    assert "Android" not in v.string()

    v = e.parseString("u@100'")[0]
    assert len(str(v.freeze({}).value)) > 100
    v2 = v.freeze({})
    v3 = v2.freeze({})
    assert v2.value.val == v3.value.val


def test_nested_response():
    e = http.NestedResponse.expr()
    v = e.parseString("s'200'")[0]
    assert v.value.val == "200"
    tutils.raises(
        language.ParseException,
        e.parseString,
        "s'foo'"
    )

    v = e.parseString('s"200:b@1"')[0]
    assert "@1" in v.spec()
    f = v.freeze({})
    assert "@1" not in f.spec()


def test_nested_response_freeze():
    e = http.NestedResponse(
        base.TokValueLiteral(
            "200:b'foo':i10,'\\x27'".encode(
                "string_escape"
            )
        )
    )
    assert e.freeze({})
    assert e.values({})


def test_unique_components():
    tutils.raises(
        "multiple body clauses",
        language.parse_pathod,
        "400:b@1:b@1"
    )
