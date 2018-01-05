import email
import time
import pytest
from unittest import mock

from mitmproxy.net.http import Headers
from mitmproxy.net.http import Response
from mitmproxy.net.http.cookies import CookieAttrs
from mitmproxy.test.tutils import tresp
from .test_message import _test_passthrough_attr


class TestResponseData:
    def test_init(self):
        with pytest.raises(ValueError):
            tresp(headers="foobar")
        with pytest.raises(UnicodeEncodeError):
            tresp(http_version="föö/bä.r")
        with pytest.raises(UnicodeEncodeError):
            tresp(reason="fööbär")
        with pytest.raises(ValueError):
            tresp(content="foobar")

        assert isinstance(tresp(headers=()).headers, Headers)


class TestResponseCore:
    """
    Tests for addons and the attributes that are directly proxied from the data structure
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
        with pytest.raises(TypeError):
            Response.make(content=42)

        r = Response.make(headers=[(b"foo", b"bar")])
        assert r.headers["foo"] == "bar"

        r = Response.make(headers=({"foo": "baz"}))
        assert r.headers["foo"] == "baz"

        with pytest.raises(TypeError):
            Response.make(headers=42)

    def test_status_code(self):
        _test_passthrough_attr(tresp(), "status_code")

    def test_reason(self):
        resp = tresp()
        assert resp.reason == "OK"

        resp.reason = "ABC"
        assert resp.data.reason == b"ABC"

        resp.reason = b"DEF"
        assert resp.data.reason == b"DEF"

        resp.reason = None
        assert resp.data.reason is None

        resp.data.reason = b'cr\xe9e'
        assert resp.reason == "crée"


class TestResponseUtils:
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
        resp.cookies = [["one", ("uno", CookieAttrs())], ["two", ("due", CookieAttrs())]]
        assert list(resp.cookies.keys()) == ["one", "two"]

    def test_refresh(self):
        r = tresp()
        n = time.time()
        r.headers["date"] = email.utils.formatdate(n)
        pre = r.headers["date"]
        r.refresh(946681202)
        assert pre == r.headers["date"]

        r.refresh(946681262)
        d = email.utils.parsedate_tz(r.headers["date"])
        d = email.utils.mktime_tz(d)
        # Weird that this is not exact...
        assert abs(60 - (d - n)) <= 1

        cookie = "MOO=BAR; Expires=Tue, 08-Mar-2011 00:20:38 GMT; Path=foo.com; Secure"
        r.headers["set-cookie"] = cookie
        r.refresh()
        # Cookie refreshing is tested in test_cookies, we just make sure that it's triggered here.
        assert cookie != r.headers["set-cookie"]

        with mock.patch('mitmproxy.net.http.cookies.refresh_set_cookie_header') as m:
            m.side_effect = ValueError
            r.refresh(n)
