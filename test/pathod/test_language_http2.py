from six.moves import cStringIO as StringIO

import netlib
from netlib import tcp
from netlib.http import user_agents

from pathod import language
from pathod.language import http2, base
import tutils


def parse_request(s):
    return language.parse_pathoc(s, True).next()


def parse_response(s):
    return language.parse_pathod(s, True).next()


def default_settings():
    return language.Settings(
        request_host="foo.com",
        protocol=netlib.http.http2.HTTP2Protocol(tcp.TCPClient(('localhost', 1234)))
    )


def test_make_error_response():
    d = StringIO()
    s = http2.make_error_response("foo", "bar")
    language.serve(s, d, default_settings())


class TestRequest:

    def test_cached_values(self):
        req = parse_request("get:/")
        req_id = id(req)
        assert req_id == id(req.resolve(default_settings()))
        assert req.values(default_settings()) == req.values(default_settings())

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

    def test_render_simple(self):
        s = StringIO()
        r = parse_request("GET:'/foo'")
        assert language.serve(
            r,
            s,
            default_settings(),
        )

    def test_raw_content_length(self):
        r = parse_request('GET:/:r')
        assert len(r.headers) == 0

        r = parse_request('GET:/:r:b"foobar"')
        assert len(r.headers) == 0

        r = parse_request('GET:/')
        assert len(r.headers) == 1
        assert r.headers[0].values(default_settings()) == ("content-length", "0")

        r = parse_request('GET:/:b"foobar"')
        assert len(r.headers) == 1
        assert r.headers[0].values(default_settings()) == ("content-length", "6")

        r = parse_request('GET:/:b"foobar":h"content-length"="42"')
        assert len(r.headers) == 1
        assert r.headers[0].values(default_settings()) == ("content-length", "42")

        r = parse_request('GET:/:r:b"foobar":h"content-length"="42"')
        assert len(r.headers) == 1
        assert r.headers[0].values(default_settings()) == ("content-length", "42")

    def test_content_type(self):
        r = parse_request('GET:/:r:c"foobar"')
        assert len(r.headers) == 1
        assert r.headers[0].values(default_settings()) == ("content-type", "foobar")

    def test_user_agent(self):
        r = parse_request('GET:/:r:ua')
        assert len(r.headers) == 1
        assert r.headers[0].values(default_settings()) == ("user-agent", user_agents.get_by_shortcut('a')[2])

    def test_render_with_headers(self):
        s = StringIO()
        r = parse_request('GET:/foo:h"foo"="bar"')
        assert language.serve(
            r,
            s,
            default_settings(),
        )

    def test_nested_response(self):
        l = "get:/p/:s'200'"
        r = parse_request(l)
        assert len(r.tokens) == 3
        assert isinstance(r.tokens[2], http2.NestedResponse)
        assert r.values(default_settings())


    def test_render_with_body(self):
        s = StringIO()
        r = parse_request("GET:'/foo':bfoobar")
        assert language.serve(
            r,
            s,
            default_settings(),
        )

    def test_spec(self):
        def rt(s):
            s = parse_request(s).spec()
            assert parse_request(s).spec() == s
        rt("get:/foo")


class TestResponse:

    def test_cached_values(self):
        res = parse_response("200")
        res_id = id(res)
        assert res_id == id(res.resolve(default_settings()))
        assert res.values(default_settings()) == res.values(default_settings())

    def test_nonascii(self):
        tutils.raises("ascii", parse_response, "200:\xf0")

    def test_err(self):
        tutils.raises(language.ParseException, parse_response, 'GET:/')

    def test_raw_content_length(self):
        r = parse_response('200:r')
        assert len(r.headers) == 0

        r = parse_response('200')
        assert len(r.headers) == 1
        assert r.headers[0].values(default_settings()) == ("content-length", "0")

    def test_content_type(self):
        r = parse_response('200:r:c"foobar"')
        assert len(r.headers) == 1
        assert r.headers[0].values(default_settings()) == ("content-type", "foobar")

    def test_simple(self):
        r = parse_response('200:r:h"foo"="bar"')
        assert r.status_code.string() == "200"
        assert len(r.headers) == 1
        assert r.headers[0].values(default_settings()) == ("foo", "bar")
        assert r.body is None

        r = parse_response('200:r:h"foo"="bar":bfoobar:h"bla"="fasel"')
        assert r.status_code.string() == "200"
        assert len(r.headers) == 2
        assert r.headers[0].values(default_settings()) == ("foo", "bar")
        assert r.headers[1].values(default_settings()) == ("bla", "fasel")
        assert r.body.string() == "foobar"

    def test_render_simple(self):
        s = StringIO()
        r = parse_response('200')
        assert language.serve(
            r,
            s,
            default_settings(),
        )

    def test_render_with_headers(self):
        s = StringIO()
        r = parse_response('200:h"foo"="bar"')
        assert language.serve(
            r,
            s,
            default_settings(),
        )

    def test_render_with_body(self):
        s = StringIO()
        r = parse_response('200:bfoobar')
        assert language.serve(
            r,
            s,
            default_settings(),
        )

    def test_spec(self):
        def rt(s):
            s = parse_response(s).spec()
            assert parse_response(s).spec() == s
        rt("200:bfoobar")
