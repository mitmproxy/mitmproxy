import mock

from netlib import tutils
from netlib import utils
from netlib.odict import ODict, ODictCaseless
from netlib.http import Request, Response, Headers, CONTENT_MISSING, HDR_FORM_URLENCODED, \
    HDR_FORM_MULTIPART


class TestRequest(object):
    def test_repr(self):
        r = tutils.treq()
        assert repr(r)

    def test_headers(self):
        tutils.raises(AssertionError, Request,
            'form_in',
            'method',
            'scheme',
            'host',
            'port',
            'path',
            b"HTTP/1.1",
            'foobar',
        )

        req = Request(
            'form_in',
            'method',
            'scheme',
            'host',
            'port',
            'path',
            b"HTTP/1.1",
        )
        assert isinstance(req.headers, Headers)

    def test_equal(self):
        a = tutils.treq(timestamp_start=42, timestamp_end=43)
        b = tutils.treq(timestamp_start=42, timestamp_end=43)
        assert a == b
        assert not a != b

        assert not a == 'foo'
        assert not b == 'foo'
        assert not 'foo' == a
        assert not 'foo' == b


    def test_anticache(self):
        req = tutils.treq()
        req.headers["If-Modified-Since"] = "foo"
        req.headers["If-None-Match"] = "bar"
        req.anticache()
        assert "If-Modified-Since" not in req.headers
        assert "If-None-Match" not in req.headers

    def test_anticomp(self):
        req = tutils.treq()
        req.headers["Accept-Encoding"] = "foobar"
        req.anticomp()
        assert req.headers["Accept-Encoding"] == "identity"

    def test_constrain_encoding(self):
        req = tutils.treq()
        req.headers["Accept-Encoding"] = "identity, gzip, foo"
        req.constrain_encoding()
        assert "foo" not in req.headers["Accept-Encoding"]

    def test_update_host(self):
        req = tutils.treq()
        req.headers["Host"] = ""
        req.host = "foobar"
        assert req.headers["Host"] == "foobar"

    def test_get_form_urlencoded(self):
        req = tutils.treq(content="foobar")
        assert req.get_form_urlencoded() == ODict()

        req.headers["Content-Type"] = HDR_FORM_URLENCODED
        assert req.get_form_urlencoded() == ODict(utils.urldecode(req.body))

    def test_get_form_multipart(self):
        req = tutils.treq(content="foobar")
        assert req.get_form_multipart() == ODict()

        req.headers["Content-Type"] = HDR_FORM_MULTIPART
        assert req.get_form_multipart() == ODict(
            utils.multipartdecode(
                req.headers,
                req.body
            )
        )

    def test_set_form_urlencoded(self):
        req = tutils.treq()
        req.set_form_urlencoded(ODict([('foo', 'bar'), ('rab', 'oof')]))
        assert req.headers["Content-Type"] == HDR_FORM_URLENCODED
        assert req.body

    def test_get_path_components(self):
        req = tutils.treq()
        assert req.get_path_components()
        # TODO: add meaningful assertions

    def test_set_path_components(self):
        req = tutils.treq()
        req.set_path_components([b"foo", b"bar"])
        # TODO: add meaningful assertions

    def test_get_query(self):
        req = tutils.treq()
        assert req.get_query().lst == []

        req.url = "http://localhost:80/foo?bar=42"
        assert req.get_query().lst == [("bar", "42")]

    def test_set_query(self):
        req = tutils.treq()
        req.set_query(ODict([]))

    def test_pretty_host(self):
        r = tutils.treq()
        assert r.pretty_host == "address"
        assert r.host == "address"
        r.headers["host"] = "other"
        assert r.pretty_host == "other"
        assert r.host == "address"
        r.host = None
        assert r.pretty_host is None
        assert r.host is None

        # Invalid IDNA
        r.headers["host"] = ".disqus.com"
        assert r.pretty_host == ".disqus.com"

    def test_pretty_url(self):
        req = tutils.treq(first_line_format="relative")
        assert req.pretty_url == "http://address:22/path"
        assert req.url == "http://address:22/path"

    def test_get_cookies_none(self):
        headers = Headers()
        r = tutils.treq()
        r.headers = headers
        assert len(r.get_cookies()) == 0

    def test_get_cookies_single(self):
        r = tutils.treq()
        r.headers = Headers(cookie="cookiename=cookievalue")
        result = r.get_cookies()
        assert len(result) == 1
        assert result['cookiename'] == ['cookievalue']

    def test_get_cookies_double(self):
        r = tutils.treq()
        r.headers = Headers(cookie="cookiename=cookievalue;othercookiename=othercookievalue")
        result = r.get_cookies()
        assert len(result) == 2
        assert result['cookiename'] == ['cookievalue']
        assert result['othercookiename'] == ['othercookievalue']

    def test_get_cookies_withequalsign(self):
        r = tutils.treq()
        r.headers = Headers(cookie="cookiename=coo=kievalue;othercookiename=othercookievalue")
        result = r.get_cookies()
        assert len(result) == 2
        assert result['cookiename'] == ['coo=kievalue']
        assert result['othercookiename'] == ['othercookievalue']

    def test_set_cookies(self):
        r = tutils.treq()
        r.headers = Headers(cookie="cookiename=cookievalue")
        result = r.get_cookies()
        result["cookiename"] = ["foo"]
        r.set_cookies(result)
        assert r.get_cookies()["cookiename"] == ["foo"]

    def test_set_url(self):
        r = tutils.treq(first_line_format="absolute")
        r.url = b"https://otheraddress:42/ORLY"
        assert r.scheme == "https"
        assert r.host == "otheraddress"
        assert r.port == 42
        assert r.path == "/ORLY"

        try:
            r.url = "//localhost:80/foo@bar"
            assert False
        except:
            assert True

    # def test_asterisk_form_in(self):
    #     f = tutils.tflow(req=None)
    #     protocol = mock_protocol("OPTIONS * HTTP/1.1")
    #     f.request = HTTPRequest.from_protocol(protocol)
    #
    #     assert f.request.first_line_format == "relative"
    #     f.request.host = f.server_conn.address.host
    #     f.request.port = f.server_conn.address.port
    #     f.request.scheme = "http"
    #     assert protocol.assemble(f.request) == (
    #         "OPTIONS * HTTP/1.1\r\n"
    #         "Host: address:22\r\n"
    #         "Content-Length: 0\r\n\r\n")
    #
    # def test_relative_form_in(self):
    #     protocol = mock_protocol("GET /foo\xff HTTP/1.1")
    #     tutils.raises("Bad HTTP request line", HTTPRequest.from_protocol, protocol)
    #
    #     protocol = mock_protocol("GET /foo HTTP/1.1\r\nConnection: Upgrade\r\nUpgrade: h2c")
    #     r = HTTPRequest.from_protocol(protocol)
    #     assert r.headers["Upgrade"] == ["h2c"]
    #
    # def test_expect_header(self):
    #     protocol = mock_protocol(
    #         "GET / HTTP/1.1\r\nContent-Length: 3\r\nExpect: 100-continue\r\n\r\nfoobar")
    #     r = HTTPRequest.from_protocol(protocol)
    #     assert protocol.tcp_handler.wfile.getvalue() == "HTTP/1.1 100 Continue\r\n\r\n"
    #     assert r.content == "foo"
    #     assert protocol.tcp_handler.rfile.read(3) == "bar"
    #
    # def test_authority_form_in(self):
    #     protocol = mock_protocol("CONNECT oops-no-port.com HTTP/1.1")
    #     tutils.raises("Bad HTTP request line", HTTPRequest.from_protocol, protocol)
    #
    #     protocol = mock_protocol("CONNECT address:22 HTTP/1.1")
    #     r = HTTPRequest.from_protocol(protocol)
    #     r.scheme, r.host, r.port = "http", "address", 22
    #     assert protocol.assemble(r) == (
    #         "CONNECT address:22 HTTP/1.1\r\n"
    #         "Host: address:22\r\n"
    #         "Content-Length: 0\r\n\r\n")
    #     assert r.pretty_url == "address:22"
    #
    # def test_absolute_form_in(self):
    #     protocol = mock_protocol("GET oops-no-protocol.com HTTP/1.1")
    #     tutils.raises("Bad HTTP request line", HTTPRequest.from_protocol, protocol)
    #
    #     protocol = mock_protocol("GET http://address:22/ HTTP/1.1")
    #     r = HTTPRequest.from_protocol(protocol)
    #     assert protocol.assemble(r) == (
    #         "GET http://address:22/ HTTP/1.1\r\n"
    #         "Host: address:22\r\n"
    #         "Content-Length: 0\r\n\r\n")
    #
    # def test_http_options_relative_form_in(self):
    #     """
    #     Exercises fix for Issue #392.
    #     """
    #     protocol = mock_protocol("OPTIONS /secret/resource HTTP/1.1")
    #     r = HTTPRequest.from_protocol(protocol)
    #     r.host = 'address'
    #     r.port = 80
    #     r.scheme = "http"
    #     assert protocol.assemble(r) == (
    #         "OPTIONS /secret/resource HTTP/1.1\r\n"
    #         "Host: address\r\n"
    #         "Content-Length: 0\r\n\r\n")
    #
    # def test_http_options_absolute_form_in(self):
    #     protocol = mock_protocol("OPTIONS http://address/secret/resource HTTP/1.1")
    #     r = HTTPRequest.from_protocol(protocol)
    #     r.host = 'address'
    #     r.port = 80
    #     r.scheme = "http"
    #     assert protocol.assemble(r) == (
    #         "OPTIONS http://address:80/secret/resource HTTP/1.1\r\n"
    #         "Host: address\r\n"
    #         "Content-Length: 0\r\n\r\n")

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
        assert repr(tutils.tresp(body=CONTENT_MISSING))

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
