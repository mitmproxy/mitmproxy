from __future__ import absolute_import, print_function, division

import email

import time

from netlib.http import Headers
from netlib.http import Response
from netlib.http.cookies import CookieAttrs
from netlib.tutils import raises, tresp
from .test_message import _test_passthrough_attr, _test_decoded_attr


class TestResponseData(object):
    def test_init(self):
        with raises(ValueError):
            tresp(headers="foobar")

        assert isinstance(tresp(headers=()).headers, Headers)


class TestResponseCore(object):
    """
    Tests for builtins and the attributes that are directly proxied from the data structure
    """
    def test_repr(self):
        response = tresp()
        assert repr(response) == "Response(200 OK, unknown content type, 7b)"
        response.content = None
        assert repr(response) == "Response(200 OK, no content)"

    def test_make(self):
        r = Response.make()
        assert r.status_code == 200
        assert r.content == b""

        r = Response.make(418, "teatime")
        assert r.status_code == 418
        assert r.content == b"teatime"
        assert r.headers["content-length"] == "7"

        Response.make(content=b"foo")
        Response.make(content="foo")
        with raises(TypeError):
            Response.make(content=42)

        r = Response.make(headers=[(b"foo", b"bar")])
        assert r.headers["foo"] == "bar"

        r = Response.make(headers=({"foo": "baz"}))
        assert r.headers["foo"] == "baz"

        with raises(TypeError):
            Response.make(headers=42)

    def test_status_code(self):
        _test_passthrough_attr(tresp(), "status_code")

    def test_reason(self):
        _test_decoded_attr(tresp(), "reason")


class TestResponseUtils(object):
    """
    Tests for additional convenience methods.
    """
    def test_get_cookies_none(self):
        resp = tresp()
        resp.headers = Headers()
        assert not resp.cookies

    def test_get_cookies_empty(self):
        resp = tresp()
        resp.headers = Headers(set_cookie="")
        assert not resp.cookies

    def test_get_cookies_simple(self):
        resp = tresp()
        resp.headers = Headers(set_cookie="cookiename=cookievalue")
        result = resp.cookies
        assert len(result) == 1
        assert "cookiename" in result
        assert result["cookiename"] == ("cookievalue", CookieAttrs())

    def test_get_cookies_with_parameters(self):
        resp = tresp()
        cookie = "cookiename=cookievalue;domain=example.com;expires=Wed Oct  21 16:29:41 2015;path=/; HttpOnly"
        resp.headers = Headers(set_cookie=cookie)
        result = resp.cookies
        assert len(result) == 1
        assert "cookiename" in result
        assert result["cookiename"][0] == "cookievalue"
        attrs = result["cookiename"][1]
        assert len(attrs) == 4
        assert attrs["domain"] == "example.com"
        assert attrs["expires"] == "Wed Oct  21 16:29:41 2015"
        assert attrs["path"] == "/"
        assert attrs["httponly"] is None

    def test_get_cookies_no_value(self):
        resp = tresp()
        resp.headers = Headers(set_cookie="cookiename=; Expires=Thu, 01-Jan-1970 00:00:01 GMT; path=/")
        result = resp.cookies
        assert len(result) == 1
        assert "cookiename" in result
        assert result["cookiename"][0] == ""
        assert len(result["cookiename"][1]) == 2

    def test_get_cookies_twocookies(self):
        resp = tresp()
        resp.headers = Headers([
            [b"Set-Cookie", b"cookiename=cookievalue"],
            [b"Set-Cookie", b"othercookie=othervalue"]
        ])
        result = resp.cookies
        assert len(result) == 2
        assert "cookiename" in result
        assert result["cookiename"] == ("cookievalue", CookieAttrs())
        assert "othercookie" in result
        assert result["othercookie"] == ("othervalue", CookieAttrs())

    def test_set_cookies(self):
        resp = tresp()
        resp.cookies["foo"] = ("bar", {})

        assert len(resp.cookies) == 1
        assert resp.cookies["foo"] == ("bar", CookieAttrs())

    def test_refresh(self):
        r = tresp()
        n = time.time()
        r.headers["date"] = email.utils.formatdate(n)
        pre = r.headers["date"]
        r.refresh(n)
        assert pre == r.headers["date"]
        r.refresh(n + 60)

        d = email.utils.parsedate_tz(r.headers["date"])
        d = email.utils.mktime_tz(d)
        # Weird that this is not exact...
        assert abs(60 - (d - n)) <= 1

        cookie = "MOO=BAR; Expires=Tue, 08-Mar-2011 00:20:38 GMT; Path=foo.com; Secure"
        r.headers["set-cookie"] = cookie
        r.refresh()
        # Cookie refreshing is tested in test_cookies, we just make sure that it's triggered here.
        assert cookie != r.headers["set-cookie"]
