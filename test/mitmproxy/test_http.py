import email
import time
import json
from unittest import mock

import pytest

from mitmproxy import flow
from mitmproxy import flowfilter
from mitmproxy.exceptions import ControlException
from mitmproxy.http import Headers, Request, Response, HTTPFlow
from mitmproxy.net.http.cookies import CookieAttrs
from mitmproxy.test.tflow import tflow
from mitmproxy.test.tutils import treq, tresp


class TestRequest:

    def test_simple(self):
        f = tflow()
        r = f.request
        u = r.url
        r.url = u
        with pytest.raises(ValueError):
            setattr(r, "url", "")
        assert r.url == u
        r2 = r.copy()
        assert r.get_state() == r2.get_state()
        assert hash(r)

    def test_get_url(self):
        r = treq()

        assert r.url == "http://address:22/path"

        r.scheme = "https"
        assert r.url == "https://address:22/path"

        r.host = "host"
        r.port = 42
        assert r.url == "https://host:42/path"

        r.host = "address"
        r.port = 22
        assert r.url == "https://address:22/path"

        assert r.pretty_url == "https://address:22/path"
        r.headers["Host"] = "foo.com:22"
        assert r.url == "https://address:22/path"
        assert r.pretty_url == "https://foo.com:22/path"

    def test_constrain_encoding(self):
        r = treq()
        r.headers["accept-encoding"] = "gzip, oink"
        r.constrain_encoding()
        assert "oink" not in r.headers["accept-encoding"]

        r.headers.set_all("accept-encoding", ["gzip", "oink"])
        r.constrain_encoding()
        assert "oink" not in r.headers["accept-encoding"]

    def test_get_content_type(self):
        resp = tresp()
        resp.headers = Headers(content_type="text/plain")
        assert resp.headers["content-type"] == "text/plain"


class TestRequestData:
    def test_init(self):
        with pytest.raises(UnicodeEncodeError):
            treq(method="fööbär")
        with pytest.raises(UnicodeEncodeError):
            treq(scheme="fööbär")
        assert treq(host="fööbär").host == "fööbär"
        with pytest.raises(UnicodeEncodeError):
            treq(path="/fööbär")
        with pytest.raises(UnicodeEncodeError):
            treq(http_version="föö/bä.r")
        with pytest.raises(ValueError):
            treq(headers="foobar")
        with pytest.raises(ValueError):
            treq(content="foobar")
        with pytest.raises(ValueError):
            treq(trailers="foobar")

        assert isinstance(treq(headers=()).headers, Headers)
        assert isinstance(treq(trailers=()).trailers, Headers)


class TestRequestCore:
    """
    Tests for addons and the attributes that are directly proxied from the data structure
    """

    def test_repr(self):
        request = treq()
        assert repr(request) == "Request(GET address:22/path)"
        request.host = None
        assert repr(request) == "Request(GET /path)"

    def test_init_conv(self):
        assert Request(
            b"example.com",
            80,
            "GET",
            "http",
            "example.com",
            "/",
            "HTTP/1.1",
            (),
            None,
            (),
            0,
            0,
        )  # type: ignore

    def test_make(self):
        r = Request.make("GET", "https://example.com/")
        assert r.method == "GET"
        assert r.scheme == "https"
        assert r.host == "example.com"
        assert r.port == 443
        assert r.path == "/"

        r = Request.make("GET", "https://example.com/", "content", {"Foo": "bar"})
        assert r.content == b"content"
        assert r.headers["content-length"] == "7"
        assert r.headers["Foo"] == "bar"

        Request.make("GET", "https://example.com/", content=b"content")
        with pytest.raises(TypeError):
            Request.make("GET", "https://example.com/", content=42)

        r = Request.make("GET", "https://example.com/", headers=[(b"foo", b"bar")])
        assert r.headers["foo"] == "bar"

        r = Request.make("GET", "https://example.com/", headers=({"foo": "baz"}))
        assert r.headers["foo"] == "baz"

        r = Request.make("GET", "https://example.com/", headers=Headers(foo="qux"))
        assert r.headers["foo"] == "qux"

        with pytest.raises(TypeError):
            Request.make("GET", "https://example.com/", headers=42)

    def test_first_line_format(self):
        assert treq(method=b"CONNECT").first_line_format == "authority"
        assert treq(authority=b"example.com").first_line_format == "absolute"
        assert treq(authority=b"").first_line_format == "relative"

    def test_method(self):
        _test_decoded_attr(treq(), "method")

    def test_scheme(self):
        _test_decoded_attr(treq(), "scheme")

    def test_port(self):
        _test_passthrough_attr(treq(), "port")

    def test_path(self):
        _test_decoded_attr(treq(), "path")

    def test_authority(self):
        request = treq()
        assert request.authority == request.data.authority.decode("idna")

        # Test IDNA encoding
        # Set str, get raw bytes
        request.authority = "ídna.example"
        assert request.data.authority == b"xn--dna-qma.example"
        # Set raw bytes, get decoded
        request.data.authority = b"xn--idn-gla.example"
        assert request.authority == "idná.example"
        # Set bytes, get raw bytes
        request.authority = b"xn--dn-qia9b.example"
        assert request.data.authority == b"xn--dn-qia9b.example"
        # IDNA encoding is not bijective
        request.authority = "fußball"
        assert request.authority == "fussball"

        # Don't fail on garbage
        request.data.authority = b"foo\xFF\x00bar"
        assert request.authority.startswith("foo")
        assert request.authority.endswith("bar")
        # foo.bar = foo.bar should not cause any side effects.
        d = request.authority
        request.authority = d
        assert request.data.authority == b"foo\xFF\x00bar"

    def test_host_update_also_updates_header(self):
        request = treq()
        assert "host" not in request.headers
        request.host = "example.com"
        assert "host" not in request.headers

        request.headers["Host"] = "foo"
        request.authority = "foo"
        request.host = "example.org"
        assert request.headers["Host"] == "example.org"
        assert request.authority == "example.org:22"

    def test_get_host_header(self):
        no_hdr = treq()
        assert no_hdr.host_header is None

        h1 = treq(
            headers=((b"host", b"header.example.com"),),
            authority=b"authority.example.com"
        )
        assert h1.host_header == "header.example.com"

        h2 = h1.copy()
        h2.http_version = "HTTP/2.0"
        assert h2.host_header == "authority.example.com"

        h2_host_only = h2.copy()
        h2_host_only.authority = ""
        assert h2_host_only.host_header == "header.example.com"

    def test_modify_host_header(self):
        h1 = treq()
        assert "host" not in h1.headers

        h1.host_header = "example.com"
        assert h1.headers["Host"] == "example.com"
        assert not h1.authority

        h1.host_header = None
        assert "host" not in h1.headers
        assert not h1.authority

        h2 = treq(http_version=b"HTTP/2.0")
        h2.host_header = "example.org"
        assert "host" not in h2.headers
        assert h2.authority == "example.org"

        h2.headers["Host"] = "example.org"
        h2.host_header = "foo.example.com"
        assert h2.headers["Host"] == "foo.example.com"
        assert h2.authority == "foo.example.com"

        h2.host_header = None
        assert "host" not in h2.headers
        assert not h2.authority


class TestRequestUtils:
    """
    Tests for additional convenience methods.
    """

    def test_url(self):
        request = treq()
        assert request.url == "http://address:22/path"

        request.url = "https://otheraddress:42/foo"
        assert request.scheme == "https"
        assert request.host == "otheraddress"
        assert request.port == 42
        assert request.path == "/foo"

        with pytest.raises(ValueError):
            request.url = "not-a-url"

    def test_url_options(self):
        request = treq(method=b"OPTIONS", path=b"*")
        assert request.url == "http://address:22"

    def test_url_authority(self):
        request = treq(method=b"CONNECT")
        assert request.url == "address:22"

    def test_pretty_host(self):
        request = treq()
        # Without host header
        assert request.pretty_host == "address"
        assert request.host == "address"
        # Same port as self.port (22)
        request.headers["host"] = "other:22"
        assert request.pretty_host == "other"

        # Invalid IDNA
        request.headers["host"] = ".disqus.com"
        assert request.pretty_host == ".disqus.com"

    def test_pretty_url(self):
        request = treq()
        # Without host header
        assert request.url == "http://address:22/path"
        assert request.pretty_url == "http://address:22/path"

        request.headers["host"] = "other:22"
        assert request.pretty_url == "http://other:22/path"

        request = treq(method=b"CONNECT", authority=b"example:44")
        assert request.pretty_url == "example:44"

    def test_pretty_url_options(self):
        request = treq(method=b"OPTIONS", path=b"*")
        assert request.pretty_url == "http://address:22"

    def test_pretty_url_authority(self):
        request = treq(method=b"CONNECT", authority="address:22")
        assert request.pretty_url == "address:22"

    def test_get_query(self):
        request = treq()
        assert not request.query

        request.url = "http://localhost:80/foo?bar=42"
        assert dict(request.query) == {"bar": "42"}

    def test_set_query(self):
        request = treq()
        assert not request.query
        request.query["foo"] = "bar"
        assert request.query["foo"] == "bar"
        assert request.path == "/path?foo=bar"
        request.query = [('foo', 'bar')]
        assert request.query["foo"] == "bar"
        assert request.path == "/path?foo=bar"

    def test_get_cookies_none(self):
        request = treq()
        request.headers = Headers()
        assert not request.cookies

    def test_get_cookies_single(self):
        request = treq()
        request.headers = Headers(cookie="cookiename=cookievalue")
        assert len(request.cookies) == 1
        assert request.cookies['cookiename'] == 'cookievalue'

    def test_get_cookies_double(self):
        request = treq()
        request.headers = Headers(cookie="cookiename=cookievalue;othercookiename=othercookievalue")
        result = request.cookies
        assert len(result) == 2
        assert result['cookiename'] == 'cookievalue'
        assert result['othercookiename'] == 'othercookievalue'

    def test_get_cookies_withequalsign(self):
        request = treq()
        request.headers = Headers(cookie="cookiename=coo=kievalue;othercookiename=othercookievalue")
        result = request.cookies
        assert len(result) == 2
        assert result['cookiename'] == 'coo=kievalue'
        assert result['othercookiename'] == 'othercookievalue'

    def test_set_cookies(self):
        request = treq()
        request.headers = Headers(cookie="cookiename=cookievalue")
        result = request.cookies
        result["cookiename"] = "foo"
        assert request.cookies["cookiename"] == "foo"
        request.cookies = [["one", "uno"], ["two", "due"]]
        assert request.cookies["one"] == "uno"
        assert request.cookies["two"] == "due"

    def test_get_path_components(self):
        request = treq(path=b"/foo/bar")
        assert request.path_components == ("foo", "bar")

    def test_set_path_components(self):
        request = treq()
        request.path_components = ["foo", "baz"]
        assert request.path == "/foo/baz"

        request.path_components = []
        assert request.path == "/"

        request.path_components = ["foo", "baz"]
        request.query["hello"] = "hello"
        assert request.path_components == ("foo", "baz")

        request.path_components = ["abc"]
        assert request.path == "/abc?hello=hello"

    def test_anticache(self):
        request = treq()
        request.headers["If-Modified-Since"] = "foo"
        request.headers["If-None-Match"] = "bar"
        request.anticache()
        assert "If-Modified-Since" not in request.headers
        assert "If-None-Match" not in request.headers

    def test_anticomp(self):
        request = treq()
        request.headers["Accept-Encoding"] = "foobar"
        request.anticomp()
        assert request.headers["Accept-Encoding"] == "identity"

    def test_constrain_encoding(self):
        request = treq()

        h = request.headers.copy()
        request.constrain_encoding()  # no-op if there is no accept_encoding header.
        assert request.headers == h

        request.headers["Accept-Encoding"] = "identity, gzip, foo"
        request.constrain_encoding()
        assert "foo" not in request.headers["Accept-Encoding"]
        assert "gzip" in request.headers["Accept-Encoding"]

    def test_get_urlencoded_form(self):
        request = treq(content=b"foobar=baz")
        assert not request.urlencoded_form

        request.headers["Content-Type"] = "application/x-www-form-urlencoded"
        assert list(request.urlencoded_form.items()) == [("foobar", "baz")]
        request.raw_content = b"\xFF"
        assert len(request.urlencoded_form) == 1

    def test_set_urlencoded_form(self):
        request = treq(content=b"\xec\xed")
        request.urlencoded_form = [('foo', 'bar'), ('rab', 'oof')]
        assert request.headers["Content-Type"] == "application/x-www-form-urlencoded"
        assert request.content

    def test_get_multipart_form(self):
        request = treq(content=b"foobar")
        assert not request.multipart_form

        request.headers["Content-Type"] = "multipart/form-data"
        assert list(request.multipart_form.items()) == []

        with mock.patch('mitmproxy.net.http.multipart.decode') as m:
            m.side_effect = ValueError
            assert list(request.multipart_form.items()) == []

    def test_set_multipart_form(self):
        request = treq()
        request.multipart_form = [(b"file", b"shell.jpg"), (b"file_size", b"1000")]
        assert request.headers["Content-Type"].startswith('multipart/form-data')
        assert list(request.multipart_form.items()) == [(b"file", b"shell.jpg"), (b"file_size", b"1000")]


class TestResponse:

    def test_simple(self):
        f = tflow(resp=True)
        resp = f.response
        resp2 = resp.copy()
        assert resp2.get_state() == resp.get_state()

    def test_get_content_type(self):
        resp = tresp()
        resp.headers = Headers(content_type="text/plain")
        assert resp.headers["content-type"] == "text/plain"


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
        with pytest.raises(ValueError):
            tresp(trailers="foobar")

        assert isinstance(tresp(headers=()).headers, Headers)
        assert isinstance(tresp(trailers=()).trailers, Headers)


class TestResponseCore:
    """
    Tests for addons and the attributes that are directly proxied from the data structure
    """

    def test_repr(self):
        response = tresp()
        assert repr(response) == "Response(200, unknown content type, 7b)"
        response.content = None
        assert repr(response) == "Response(200, no content)"

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

        r = Response.make(headers=Headers(foo="qux"))
        assert r.headers["foo"] == "qux"

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
        assert attrs["httponly"] == ""

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
        r.headers["date"] = email.utils.formatdate(n, usegmt=True)
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


class TestHTTPFlow:

    def test_copy(self):
        f = tflow(resp=True)
        assert repr(f)
        f.get_state()
        f2 = f.copy()
        a = f.get_state()
        b = f2.get_state()
        del a["id"]
        del b["id"]
        assert a == b
        assert not f == f2
        assert f is not f2
        assert f.request.get_state() == f2.request.get_state()
        assert f.request is not f2.request
        assert f.request.headers == f2.request.headers
        assert f.request.headers is not f2.request.headers
        assert f.response.get_state() == f2.response.get_state()
        assert f.response is not f2.response

        f = tflow(err=True)
        f2 = f.copy()
        assert f is not f2
        assert f.request is not f2.request
        assert f.request.headers == f2.request.headers
        assert f.request.headers is not f2.request.headers
        assert f.error.get_state() == f2.error.get_state()
        assert f.error is not f2.error

    def test_match(self):
        f = tflow(resp=True)
        assert not flowfilter.match("~b test", f)
        assert flowfilter.match(None, f)
        assert not flowfilter.match("~b test", f)

        f = tflow(err=True)
        assert flowfilter.match("~e", f)

        with pytest.raises(ValueError):
            flowfilter.match("~", f)

    def test_backup(self):
        f = tflow()
        f.response = tresp()
        f.request.content = b"foo"
        assert not f.modified()
        f.backup()
        f.request.content = b"bar"
        assert f.modified()
        f.revert()
        assert f.request.content == b"foo"

    def test_backup_idempotence(self):
        f = tflow(resp=True)
        f.backup()
        f.revert()
        f.backup()
        f.revert()

    def test_getset_state(self):
        f = tflow(resp=True)
        state = f.get_state()
        assert f.get_state() == HTTPFlow.from_state(
            state).get_state()

        f.response = None
        f.error = flow.Error("error")
        state = f.get_state()
        assert f.get_state() == HTTPFlow.from_state(
            state).get_state()

        f2 = f.copy()
        f2.id = f.id  # copy creates a different uuid
        assert f.get_state() == f2.get_state()
        assert not f == f2
        f2.error = flow.Error("e2")
        assert not f == f2
        f2.backup()
        f2.intercept()  # to change the state
        f.set_state(f2.get_state())
        assert f.get_state() == f2.get_state()

    def test_kill(self):
        f = tflow()
        with pytest.raises(ControlException):
            f.intercept()
            f.resume()
            f.kill()

        f = tflow()
        f.intercept()
        assert f.killable
        f.kill()
        assert not f.killable
        assert f.error.msg == flow.Error.KILLED_MESSAGE

    def test_intercept(self):
        f = tflow()
        f.intercept()
        assert f.reply.state == "taken"
        f.intercept()
        assert f.reply.state == "taken"

    def test_resume(self):
        f = tflow()
        f.intercept()
        assert f.reply.state == "taken"
        f.resume()
        assert f.reply.state == "committed"

    def test_resume_duplicated(self):
        f = tflow()
        f.intercept()
        f2 = f.copy()
        assert f.intercepted is f2.intercepted is True
        f.resume()
        f2.resume()
        assert f.intercepted is f2.intercepted is False

    def test_timestamp_start(self):
        f = tflow()
        assert f.timestamp_start == f.request.timestamp_start


class TestHeaders:
    def _2host(self):
        return Headers(
            (
                (b"Host", b"example.com"),
                (b"host", b"example.org")
            )
        )

    def test_init(self):
        headers = Headers()
        assert len(headers) == 0

        headers = Headers([(b"Host", b"example.com")])
        assert len(headers) == 1
        assert headers["Host"] == "example.com"

        headers = Headers(Host="example.com")
        assert len(headers) == 1
        assert headers["Host"] == "example.com"

        headers = Headers(
            [(b"Host", b"invalid")],
            Host="example.com"
        )
        assert len(headers) == 1
        assert headers["Host"] == "example.com"

        headers = Headers(
            [(b"Host", b"invalid"), (b"Accept", b"text/plain")],
            Host="example.com"
        )
        assert len(headers) == 2
        assert headers["Host"] == "example.com"
        assert headers["Accept"] == "text/plain"

        with pytest.raises(TypeError):
            Headers([(b"Host", "not-bytes")])

    def test_set(self):
        headers = Headers()
        headers["foo"] = "1"
        headers[b"bar"] = b"2"
        headers["baz"] = b"3"
        with pytest.raises(TypeError):
            headers["foobar"] = 42
        assert len(headers) == 3

    def test_bytes(self):
        headers = Headers(Host="example.com")
        assert bytes(headers) == b"Host: example.com\r\n"

        headers = Headers([
            (b"Host", b"example.com"),
            (b"Accept", b"text/plain")
        ])
        assert bytes(headers) == b"Host: example.com\r\nAccept: text/plain\r\n"

        headers = Headers()
        assert bytes(headers) == b""

    def test_iter(self):
        headers = Headers([
            (b"Set-Cookie", b"foo"),
            (b"Set-Cookie", b"bar")
        ])
        assert list(headers) == ["Set-Cookie"]

    def test_insert(self):
        headers = Headers(Accept="text/plain")
        headers.insert(0, b"Host", "example.com")
        assert headers.fields == (
            (b'Host', b'example.com'),
            (b'Accept', b'text/plain')
        )

    def test_items(self):
        headers = Headers([
            (b"Set-Cookie", b"foo"),
            (b"Set-Cookie", b"bar"),
            (b'Accept', b'text/plain'),
        ])
        assert list(headers.items()) == [
            ('Set-Cookie', 'foo, bar'),
            ('Accept', 'text/plain')
        ]
        assert list(headers.items(multi=True)) == [
            ('Set-Cookie', 'foo'),
            ('Set-Cookie', 'bar'),
            ('Accept', 'text/plain')
        ]


def _test_passthrough_attr(message, attr):
    assert getattr(message, attr) == getattr(message.data, attr)
    setattr(message, attr, b"foo")
    assert getattr(message.data, attr) == b"foo"


def _test_decoded_attr(message, attr):
    assert getattr(message, attr) == getattr(message.data, attr).decode("utf8")
    # Set str, get raw bytes
    setattr(message, attr, "foo")
    assert getattr(message.data, attr) == b"foo"
    # Set raw bytes, get decoded
    setattr(message.data, attr, b"BAR")  # use uppercase so that we can also cover request.method
    assert getattr(message, attr) == "BAR"
    # Set bytes, get raw bytes
    setattr(message, attr, b"baz")
    assert getattr(message.data, attr) == b"baz"

    # Set UTF8
    setattr(message, attr, "Non-Autorisé")
    assert getattr(message.data, attr) == b"Non-Autoris\xc3\xa9"
    # Don't fail on garbage
    setattr(message.data, attr, b"FOO\xBF\x00BAR")
    assert getattr(message, attr).startswith("FOO")
    assert getattr(message, attr).endswith("BAR")
    # foo.bar = foo.bar should not cause any side effects.
    d = getattr(message, attr)
    setattr(message, attr, d)
    assert getattr(message.data, attr) == b"FOO\xBF\x00BAR"


class TestMessageData:
    def test_eq(self):
        data = tresp(timestamp_start=42, timestamp_end=42).data
        same = tresp(timestamp_start=42, timestamp_end=42).data
        assert data == same

        other = tresp(content=b"foo").data
        assert data != other

        assert data != 0

    def test_serializable(self):
        data1 = tresp(timestamp_start=42, timestamp_end=42).data
        data1.trailers = Headers()
        data2 = tresp().data.from_state(data1.get_state())  # ResponseData.from_state()

        assert data1 == data2


class TestMessage:

    def test_init(self):
        resp = tresp()
        assert resp.data

    def test_eq_ne(self):
        resp = tresp(timestamp_start=42, timestamp_end=42)
        same = tresp(timestamp_start=42, timestamp_end=42)
        assert resp.data == same.data

        other = tresp(timestamp_start=0, timestamp_end=0)
        assert resp.data != other.data

        assert resp != 0

    def test_serializable(self):
        resp = tresp()
        resp.trailers = Headers()
        resp2 = Response.from_state(resp.get_state())
        assert resp.data == resp2.data

    def test_content_length_update(self):
        resp = tresp()
        resp.content = b"foo"
        assert resp.data.content == b"foo"
        assert resp.headers["content-length"] == "3"
        resp.content = b""
        assert resp.data.content == b""
        assert resp.headers["content-length"] == "0"
        resp.raw_content = b"bar"
        assert resp.data.content == b"bar"
        assert resp.headers["content-length"] == "0"

    def test_content_length_not_added_for_response_with_transfer_encoding(self):
        headers = Headers(((b"transfer-encoding", b"chunked"),))
        resp = tresp(headers=headers)
        resp.content = b"bar"

        assert "content-length" not in resp.headers

    def test_headers(self):
        _test_passthrough_attr(tresp(), "headers")

    def test_trailers(self):
        _test_passthrough_attr(tresp(), "trailers")

    def test_timestamp_start(self):
        _test_passthrough_attr(tresp(), "timestamp_start")

    def test_timestamp_end(self):
        _test_passthrough_attr(tresp(), "timestamp_end")

    def test_http_version(self):
        _test_decoded_attr(tresp(), "http_version")
        assert tresp(http_version=b"HTTP/1.0").is_http10
        assert tresp(http_version=b"HTTP/1.1").is_http11
        assert tresp(http_version=b"HTTP/2.0").is_http2


class TestMessageContentEncoding:
    def test_simple(self):
        r = tresp()
        assert r.raw_content == b"message"
        assert "content-encoding" not in r.headers
        r.encode("gzip")

        assert r.headers["content-encoding"]
        assert r.raw_content != b"message"
        assert r.content == b"message"
        assert r.raw_content != b"message"

    def test_update_content_length_header(self):
        r = tresp()
        assert int(r.headers["content-length"]) == 7
        r.encode("gzip")
        assert int(r.headers["content-length"]) == 27
        r.decode()
        assert int(r.headers["content-length"]) == 7

    def test_modify(self):
        r = tresp()
        assert "content-encoding" not in r.headers
        r.encode("gzip")

        r.content = b"foo"
        assert r.raw_content != b"foo"
        r.decode()
        assert r.raw_content == b"foo"

        with pytest.raises(TypeError):
            r.content = "foo"

    def test_unknown_ce(self):
        r = tresp()
        r.headers["content-encoding"] = "zopfli"
        r.raw_content = b"foo"
        with pytest.raises(ValueError):
            assert r.content
        assert r.headers["content-encoding"]
        assert r.get_content(strict=False) == b"foo"

    def test_utf8_as_ce(self):
        r = tresp()
        r.headers["content-encoding"] = "utf8"
        r.raw_content = b"foo"
        with pytest.raises(ValueError):
            assert r.content
        assert r.headers["content-encoding"]
        assert r.get_content(strict=False) == b"foo"

    def test_cannot_decode(self):
        r = tresp()
        r.encode("gzip")
        r.raw_content = b"foo"
        with pytest.raises(ValueError):
            assert r.content
        assert r.headers["content-encoding"]
        assert r.get_content(strict=False) == b"foo"

        with pytest.raises(ValueError):
            r.decode()
        assert r.raw_content == b"foo"
        assert "content-encoding" in r.headers

        r.decode(strict=False)
        assert r.content == b"foo"
        assert "content-encoding" not in r.headers

    def test_none(self):
        r = tresp(content=None)
        assert r.content is None
        r.content = b"foo"
        assert r.content is not None
        r.content = None
        assert r.content is None

    def test_cannot_encode(self):
        r = tresp()
        r.encode("gzip")
        r.content = None
        assert r.headers["content-encoding"]
        assert r.raw_content is None

        r.headers["content-encoding"] = "zopfli"
        r.content = b"foo"
        assert "content-encoding" not in r.headers
        assert r.raw_content == b"foo"

        with pytest.raises(ValueError):
            r.encode("zopfli")
        assert r.raw_content == b"foo"
        assert "content-encoding" not in r.headers


class TestMessageText:
    def test_simple(self):
        r = tresp(content=b'\xfc')
        assert r.raw_content == b"\xfc"
        assert r.content == b"\xfc"
        assert r.text == "ü"

        r.encode("gzip")
        assert r.text == "ü"
        r.decode()
        assert r.text == "ü"

        r.headers["content-type"] = "text/html; charset=latin1"
        r.content = b"\xc3\xbc"
        assert r.text == "Ã¼"
        r.headers["content-type"] = "text/html; charset=utf8"
        assert r.text == "ü"

    def test_guess_json(self):
        r = tresp(content=b'"\xc3\xbc"')
        r.headers["content-type"] = "application/json"
        assert r.text == '"ü"'

    def test_guess_meta_charset(self):
        r = tresp(content=b'<meta http-equiv="content-type" '
                          b'content="text/html;charset=gb2312">\xe6\x98\x8e\xe4\xbc\xaf')
        # "鏄庝集" is decoded form of \xe6\x98\x8e\xe4\xbc\xaf in gb18030
        assert "鏄庝集" in r.text

    def test_guess_css_charset(self):
        # @charset but not text/css
        r = tresp(content=b'@charset "gb2312";'
                          b'#foo::before {content: "\xe6\x98\x8e\xe4\xbc\xaf"}')
        # "鏄庝集" is decoded form of \xe6\x98\x8e\xe4\xbc\xaf in gb18030
        assert "鏄庝集" not in r.text

        # @charset not at the beginning
        r = tresp(content=b'foo@charset "gb2312";'
                          b'#foo::before {content: "\xe6\x98\x8e\xe4\xbc\xaf"}')
        r.headers["content-type"] = "text/css"
        # "鏄庝集" is decoded form of \xe6\x98\x8e\xe4\xbc\xaf in gb18030
        assert "鏄庝集" not in r.text

        # @charset and text/css
        r = tresp(content=b'@charset "gb2312";'
                          b'#foo::before {content: "\xe6\x98\x8e\xe4\xbc\xaf"}')
        r.headers["content-type"] = "text/css"
        # "鏄庝集" is decoded form of \xe6\x98\x8e\xe4\xbc\xaf in gb18030
        assert "鏄庝集" in r.text

    def test_guess_latin_1(self):
        r = tresp(content=b"\xF0\xE2")
        assert r.text == "ðâ"

    def test_none(self):
        r = tresp(content=None)
        assert r.text is None
        r.text = "foo"
        assert r.text is not None
        r.text = None
        assert r.text is None

    def test_modify(self):
        r = tresp()

        r.text = "ü"
        assert r.raw_content == b"\xfc"

        r.headers["content-type"] = "text/html; charset=utf8"
        r.text = "ü"
        assert r.raw_content == b"\xc3\xbc"
        assert r.headers["content-length"] == "2"

    def test_unknown_ce(self):
        r = tresp()
        r.headers["content-type"] = "text/html; charset=wtf"
        r.raw_content = b"foo"
        with pytest.raises(ValueError):
            assert r.text == "foo"
        assert r.get_text(strict=False) == "foo"

    def test_cannot_decode(self):
        r = tresp()
        r.headers["content-type"] = "text/html; charset=utf8"
        r.raw_content = b"\xFF"
        with pytest.raises(ValueError):
            assert r.text

        assert r.get_text(strict=False) == '\udcff'

    def test_cannot_encode(self):
        r = tresp()
        r.content = None
        assert "content-type" not in r.headers
        assert r.raw_content is None

        r.headers["content-type"] = "text/html; charset=latin1; foo=bar"
        r.text = "☃"
        assert r.headers["content-type"] == "text/html; charset=utf-8; foo=bar"
        assert r.raw_content == b'\xe2\x98\x83'

        r.headers["content-type"] = "gibberish"
        r.text = "☃"
        assert r.headers["content-type"] == "text/plain; charset=utf-8"
        assert r.raw_content == b'\xe2\x98\x83'

        del r.headers["content-type"]
        r.text = "☃"
        assert r.headers["content-type"] == "text/plain; charset=utf-8"
        assert r.raw_content == b'\xe2\x98\x83'

        r.headers["content-type"] = "text/html; charset=latin1"
        r.text = '\udcff'
        assert r.headers["content-type"] == "text/html; charset=utf-8"
        assert r.raw_content == b"\xFF"

    def test_get_json(self):
        req = treq(content=None)
        with pytest.raises(TypeError):
            req.json()

        req = treq(content=b'')
        with pytest.raises(json.decoder.JSONDecodeError):
            req.json()

        req = treq(content=b'{}')
        assert req.json() == {}

        req = treq(content=b'{"a": 1}')
        assert req.json() == {"a": 1}

        req = treq(content=b'{')

        with pytest.raises(json.decoder.JSONDecodeError):
            req.json()
