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
        req.update_host_header()
        assert req.headers["Host"] == "foobar"

    def test_get_form(self):
        req = tutils.treq()
        assert req.get_form() == ODict()

    @mock.patch("netlib.http.Request.get_form_multipart")
    @mock.patch("netlib.http.Request.get_form_urlencoded")
    def test_get_form_with_url_encoded(self, mock_method_urlencoded, mock_method_multipart):
        req = tutils.treq()
        assert req.get_form() == ODict()

        req = tutils.treq()
        req.body = "foobar"
        req.headers["Content-Type"] = HDR_FORM_URLENCODED
        req.get_form()
        assert req.get_form_urlencoded.called
        assert not req.get_form_multipart.called

    @mock.patch("netlib.http.Request.get_form_multipart")
    @mock.patch("netlib.http.Request.get_form_urlencoded")
    def test_get_form_with_multipart(self, mock_method_urlencoded, mock_method_multipart):
        req = tutils.treq()
        req.body = "foobar"
        req.headers["Content-Type"] = HDR_FORM_MULTIPART
        req.get_form()
        assert not req.get_form_urlencoded.called
        assert req.get_form_multipart.called

    def test_get_form_urlencoded(self):
        req = tutils.treq(body="foobar")
        assert req.get_form_urlencoded() == ODict()

        req.headers["Content-Type"] = HDR_FORM_URLENCODED
        assert req.get_form_urlencoded() == ODict(utils.urldecode(req.body))

    def test_get_form_multipart(self):
        req = tutils.treq(body="foobar")
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
        req.set_path_components(["foo", "bar"])
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
        assert r.pretty_host(True) == "address"
        assert r.pretty_host(False) == "address"
        r.headers["host"] = "other"
        assert r.pretty_host(True) == "other"
        assert r.pretty_host(False) == "address"
        r.host = None
        assert r.pretty_host(True) == "other"
        assert r.pretty_host(False) is None
        del r.headers["host"]
        assert r.pretty_host(True) is None
        assert r.pretty_host(False) is None

        # Invalid IDNA
        r.headers["host"] = ".disqus.com"
        assert r.pretty_host(True) == ".disqus.com"

    def test_pretty_url(self):
        req = tutils.treq()
        req.form_out = "authority"
        assert req.pretty_url(True) == "address:22"
        assert req.pretty_url(False) == "address:22"

        req.form_out = "relative"
        assert req.pretty_url(True) == "http://address:22/path"
        assert req.pretty_url(False) == "http://address:22/path"

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
        r = tutils.treq(form_in="absolute")
        r.url = "https://otheraddress:42/ORLY"
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
    #     assert f.request.form_in == "relative"
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
    #     assert r.pretty_url(False) == "address:22"
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
            ["Set-Cookie", "cookiename=cookievalue"],
            ["Set-Cookie", "othercookie=othervalue"]
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


class TestHeaders(object):
    def _2host(self):
        return Headers(
            [
                ["Host", "example.com"],
                ["host", "example.org"]
            ]
        )

    def test_init(self):
        headers = Headers()
        assert len(headers) == 0

        headers = Headers([["Host", "example.com"]])
        assert len(headers) == 1
        assert headers["Host"] == "example.com"

        headers = Headers(Host="example.com")
        assert len(headers) == 1
        assert headers["Host"] == "example.com"

        headers = Headers(
            [["Host", "invalid"]],
            Host="example.com"
        )
        assert len(headers) == 1
        assert headers["Host"] == "example.com"

        headers = Headers(
            [["Host", "invalid"], ["Accept", "text/plain"]],
            Host="example.com"
        )
        assert len(headers) == 2
        assert headers["Host"] == "example.com"
        assert headers["Accept"] == "text/plain"

    def test_getitem(self):
        headers = Headers(Host="example.com")
        assert headers["Host"] == "example.com"
        assert headers["host"] == "example.com"
        tutils.raises(KeyError, headers.__getitem__, "Accept")

        headers = self._2host()
        assert headers["Host"] == "example.com, example.org"

    def test_str(self):
        headers = Headers(Host="example.com")
        assert bytes(headers) == "Host: example.com\r\n"

        headers = Headers([
            ["Host", "example.com"],
            ["Accept", "text/plain"]
        ])
        assert str(headers) == "Host: example.com\r\nAccept: text/plain\r\n"

    def test_setitem(self):
        headers = Headers()
        headers["Host"] = "example.com"
        assert "Host" in headers
        assert "host" in headers
        assert headers["Host"] == "example.com"

        headers["host"] = "example.org"
        assert "Host" in headers
        assert "host" in headers
        assert headers["Host"] == "example.org"

        headers["accept"] = "text/plain"
        assert len(headers) == 2
        assert "Accept" in headers
        assert "Host" in headers

        headers = self._2host()
        assert len(headers.fields) == 2
        headers["Host"] = "example.com"
        assert len(headers.fields) == 1
        assert "Host" in headers

    def test_delitem(self):
        headers = Headers(Host="example.com")
        assert len(headers) == 1
        del headers["host"]
        assert len(headers) == 0
        try:
            del headers["host"]
        except KeyError:
            assert True
        else:
            assert False

        headers = self._2host()
        del headers["Host"]
        assert len(headers) == 0

    def test_keys(self):
        headers = Headers(Host="example.com")
        assert len(headers.keys()) == 1
        assert headers.keys()[0] == "Host"

        headers = self._2host()
        assert len(headers.keys()) == 1
        assert headers.keys()[0] == "Host"

    def test_eq_ne(self):
        headers1 = Headers(Host="example.com")
        headers2 = Headers(host="example.com")
        assert not (headers1 == headers2)
        assert headers1 != headers2

        headers1 = Headers(Host="example.com")
        headers2 = Headers(Host="example.com")
        assert headers1 == headers2
        assert not (headers1 != headers2)

        assert headers1 != 42

    def test_get_all(self):
        headers = self._2host()
        assert headers.get_all("host") == ["example.com", "example.org"]
        assert headers.get_all("accept") == []

    def test_set_all(self):
        headers = Headers(Host="example.com")
        headers.set_all("Accept", ["text/plain"])
        assert len(headers) == 2
        assert "accept" in headers

        headers = self._2host()
        headers.set_all("Host", ["example.org"])
        assert headers["host"] == "example.org"

        headers.set_all("Host", ["example.org", "example.net"])
        assert headers["host"] == "example.org, example.net"

    def test_state(self):
        headers = self._2host()
        assert len(headers.get_state()) == 2
        assert headers == Headers.from_state(headers.get_state())

        headers2 = Headers()
        assert headers != headers2
        headers2.load_state(headers.get_state())
        assert headers == headers2
