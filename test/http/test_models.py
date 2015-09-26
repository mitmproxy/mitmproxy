
from netlib import tutils
from netlib.odict import ODict, ODictCaseless
from netlib.http import Response, Headers, CONTENT_MISSING

class TestResponse(object):
    def test_headers(self):
        tutils.raises(AssertionError, Response,
            b"HTTP/1.1",
            200,
            headers='foobar',
        )

        resp = Response(
            b"HTTP/1.1",
            200,
        )
        assert isinstance(resp.headers, Headers)

    def test_equal(self):
        a = tutils.tresp(timestamp_start=42, timestamp_end=43)
        b = tutils.tresp(timestamp_start=42, timestamp_end=43)
        assert a == b

        assert not a == 'foo'
        assert not b == 'foo'
        assert not 'foo' == a
        assert not 'foo' == b

    def test_repr(self):
        r = tutils.tresp()
        assert "unknown content type" in repr(r)
        r.headers["content-type"] = "foo"
        assert "foo" in repr(r)
        assert repr(tutils.tresp(content=CONTENT_MISSING))

    def test_get_cookies_none(self):
        resp = tutils.tresp()
        resp.headers = Headers()
        assert not resp.get_cookies()

    def test_get_cookies_simple(self):
        resp = tutils.tresp()
        resp.headers = Headers(set_cookie="cookiename=cookievalue")
        result = resp.get_cookies()
        assert len(result) == 1
        assert "cookiename" in result
        assert result["cookiename"][0] == ["cookievalue", ODict()]

    def test_get_cookies_with_parameters(self):
        resp = tutils.tresp()
        resp.headers = Headers(set_cookie="cookiename=cookievalue;domain=example.com;expires=Wed Oct  21 16:29:41 2015;path=/; HttpOnly")
        result = resp.get_cookies()
        assert len(result) == 1
        assert "cookiename" in result
        assert result["cookiename"][0][0] == "cookievalue"
        attrs = result["cookiename"][0][1]
        assert len(attrs) == 4
        assert attrs["domain"] == ["example.com"]
        assert attrs["expires"] == ["Wed Oct  21 16:29:41 2015"]
        assert attrs["path"] == ["/"]
        assert attrs["httponly"] == [None]

    def test_get_cookies_no_value(self):
        resp = tutils.tresp()
        resp.headers = Headers(set_cookie="cookiename=; Expires=Thu, 01-Jan-1970 00:00:01 GMT; path=/")
        result = resp.get_cookies()
        assert len(result) == 1
        assert "cookiename" in result
        assert result["cookiename"][0][0] == ""
        assert len(result["cookiename"][0][1]) == 2

    def test_get_cookies_twocookies(self):
        resp = tutils.tresp()
        resp.headers = Headers([
            [b"Set-Cookie", b"cookiename=cookievalue"],
            [b"Set-Cookie", b"othercookie=othervalue"]
        ])
        result = resp.get_cookies()
        assert len(result) == 2
        assert "cookiename" in result
        assert result["cookiename"][0] == ["cookievalue", ODict()]
        assert "othercookie" in result
        assert result["othercookie"][0] == ["othervalue", ODict()]

    def test_set_cookies(self):
        resp = tutils.tresp()
        v = resp.get_cookies()
        v.add("foo", ["bar", ODictCaseless()])
        resp.set_cookies(v)

        v = resp.get_cookies()
        assert len(v) == 1
        assert v["foo"] == [["bar", ODictCaseless()]]
