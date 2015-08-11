import mock

from netlib import http
from netlib import odict
from netlib import tutils
from netlib import utils
from netlib.http import semantics
from netlib.http.semantics import CONTENT_MISSING

class TestProtocolMixin(object):
    @mock.patch("netlib.http.semantics.ProtocolMixin.assemble_response")
    @mock.patch("netlib.http.semantics.ProtocolMixin.assemble_request")
    def test_assemble_request(self, mock_request_method, mock_response_method):
        p = semantics.ProtocolMixin()
        p.assemble(tutils.treq())
        assert mock_request_method.called
        assert not mock_response_method.called

    @mock.patch("netlib.http.semantics.ProtocolMixin.assemble_response")
    @mock.patch("netlib.http.semantics.ProtocolMixin.assemble_request")
    def test_assemble_response(self, mock_request_method, mock_response_method):
        p = semantics.ProtocolMixin()
        p.assemble(tutils.tresp())
        assert not mock_request_method.called
        assert mock_response_method.called

    def test_assemble_foo(self):
        p = semantics.ProtocolMixin()
        tutils.raises(ValueError, p.assemble, 'foo')

class TestRequest(object):
    def test_repr(self):
        r = tutils.treq()
        assert repr(r)

    def test_headers_odict(self):
        tutils.raises(AssertionError, semantics.Request,
            'form_in',
            'method',
            'scheme',
            'host',
            'port',
            'path',
            (1, 1),
            'foobar',
        )

        req = semantics.Request(
            'form_in',
            'method',
            'scheme',
            'host',
            'port',
            'path',
            (1, 1),
        )
        assert isinstance(req.headers, odict.ODictCaseless)

    def test_equal(self):
        a = tutils.treq()
        b = tutils.treq()
        assert a == b

        assert not a == 'foo'
        assert not b == 'foo'
        assert not 'foo' == a
        assert not 'foo' == b

    def test_legacy_first_line(self):
        req = tutils.treq()

        req.form_in = 'relative'
        assert req.legacy_first_line() == "GET /path HTTP/1.1"

        req.form_in = 'authority'
        assert req.legacy_first_line() == "GET address:22 HTTP/1.1"

        req.form_in = 'absolute'
        assert req.legacy_first_line() == "GET http://address:22/path HTTP/1.1"

        req.form_in = 'foobar'
        tutils.raises(http.HttpError, req.legacy_first_line)

    def test_anticache(self):
        req = tutils.treq()
        req.headers.add("If-Modified-Since", "foo")
        req.headers.add("If-None-Match", "bar")
        req.anticache()
        assert "If-Modified-Since" not in req.headers
        assert "If-None-Match" not in req.headers

    def test_anticomp(self):
        req = tutils.treq()
        req.headers.add("Accept-Encoding", "foobar")
        req.anticomp()
        assert req.headers["Accept-Encoding"] == ["identity"]

    def test_constrain_encoding(self):
        req = tutils.treq()
        req.headers.add("Accept-Encoding", "identity, gzip, foo")
        req.constrain_encoding()
        assert "foo" not in req.headers.get_first("Accept-Encoding")

    def test_update_host(self):
        req = tutils.treq()
        req.headers.add("Host", "")
        req.host = "foobar"
        req.update_host_header()
        assert req.headers.get_first("Host") == "foobar"

    def test_get_form(self):
        req = tutils.treq()
        assert req.get_form() == odict.ODict()

    @mock.patch("netlib.http.semantics.Request.get_form_multipart")
    @mock.patch("netlib.http.semantics.Request.get_form_urlencoded")
    def test_get_form_with_url_encoded(self, mock_method_urlencoded, mock_method_multipart):
        req = tutils.treq()
        assert req.get_form() == odict.ODict()

        req = tutils.treq()
        req.body = "foobar"
        req.headers["Content-Type"] = [semantics.HDR_FORM_URLENCODED]
        req.get_form()
        assert req.get_form_urlencoded.called
        assert not req.get_form_multipart.called

    @mock.patch("netlib.http.semantics.Request.get_form_multipart")
    @mock.patch("netlib.http.semantics.Request.get_form_urlencoded")
    def test_get_form_with_multipart(self, mock_method_urlencoded, mock_method_multipart):
        req = tutils.treq()
        req.body = "foobar"
        req.headers["Content-Type"] = [semantics.HDR_FORM_MULTIPART]
        req.get_form()
        assert not req.get_form_urlencoded.called
        assert req.get_form_multipart.called

    def test_get_form_urlencoded(self):
        req = tutils.treq("foobar")
        assert req.get_form_urlencoded() == odict.ODict()

        req.headers["Content-Type"] = [semantics.HDR_FORM_URLENCODED]
        assert req.get_form_urlencoded() == odict.ODict(utils.urldecode(req.body))

    def test_get_form_multipart(self):
        req = tutils.treq("foobar")
        assert req.get_form_multipart() == odict.ODict()

        req.headers["Content-Type"] = [semantics.HDR_FORM_MULTIPART]
        assert req.get_form_multipart() == odict.ODict(
            utils.multipartdecode(
                req.headers,
                req.body))

    def test_set_form_urlencoded(self):
        req = tutils.treq()
        req.set_form_urlencoded(odict.ODict([('foo', 'bar'), ('rab', 'oof')]))
        assert req.headers.get_first("Content-Type") == semantics.HDR_FORM_URLENCODED
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
        req.set_query(odict.ODict([]))

    def test_pretty_host(self):
        r = tutils.treq()
        assert r.pretty_host(True) == "address"
        assert r.pretty_host(False) == "address"
        r.headers["host"] = ["other"]
        assert r.pretty_host(True) == "other"
        assert r.pretty_host(False) == "address"
        r.host = None
        assert r.pretty_host(True) == "other"
        assert r.pretty_host(False) is None
        del r.headers["host"]
        assert r.pretty_host(True) is None
        assert r.pretty_host(False) is None

        # Invalid IDNA
        r.headers["host"] = [".disqus.com"]
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
        h = odict.ODictCaseless()
        r = tutils.treq()
        r.headers = h
        assert len(r.get_cookies()) == 0

    def test_get_cookies_single(self):
        h = odict.ODictCaseless()
        h["Cookie"] = ["cookiename=cookievalue"]
        r = tutils.treq()
        r.headers = h
        result = r.get_cookies()
        assert len(result) == 1
        assert result['cookiename'] == ['cookievalue']

    def test_get_cookies_double(self):
        h = odict.ODictCaseless()
        h["Cookie"] = [
            "cookiename=cookievalue;othercookiename=othercookievalue"
        ]
        r = tutils.treq()
        r.headers = h
        result = r.get_cookies()
        assert len(result) == 2
        assert result['cookiename'] == ['cookievalue']
        assert result['othercookiename'] == ['othercookievalue']

    def test_get_cookies_withequalsign(self):
        h = odict.ODictCaseless()
        h["Cookie"] = [
            "cookiename=coo=kievalue;othercookiename=othercookievalue"
        ]
        r = tutils.treq()
        r.headers = h
        result = r.get_cookies()
        assert len(result) == 2
        assert result['cookiename'] == ['coo=kievalue']
        assert result['othercookiename'] == ['othercookievalue']

    def test_set_cookies(self):
        h = odict.ODictCaseless()
        h["Cookie"] = ["cookiename=cookievalue"]
        r = tutils.treq()
        r.headers = h
        result = r.get_cookies()
        result["cookiename"] = ["foo"]
        r.set_cookies(result)
        assert r.get_cookies()["cookiename"] == ["foo"]

    def test_set_url(self):
        r = tutils.treq_absolute()
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

class TestEmptyRequest(object):
    def test_init(self):
        req = semantics.EmptyRequest()
        assert req

class TestResponse(object):
    def test_headers_odict(self):
        tutils.raises(AssertionError, semantics.Response,
            (1, 1),
            200,
            headers='foobar',
        )

        resp = semantics.Response(
            (1, 1),
            200,
        )
        assert isinstance(resp.headers, odict.ODictCaseless)

    def test_equal(self):
        a = tutils.tresp()
        b = tutils.tresp()
        assert a == b

        assert not a == 'foo'
        assert not b == 'foo'
        assert not 'foo' == a
        assert not 'foo' == b

    def test_repr(self):
        r = tutils.tresp()
        assert "unknown content type" in repr(r)
        r.headers["content-type"] = ["foo"]
        assert "foo" in repr(r)
        assert repr(tutils.tresp(content=CONTENT_MISSING))

    def test_get_cookies_none(self):
        h = odict.ODictCaseless()
        resp = tutils.tresp()
        resp.headers = h
        assert not resp.get_cookies()

    def test_get_cookies_simple(self):
        h = odict.ODictCaseless()
        h["Set-Cookie"] = ["cookiename=cookievalue"]
        resp = tutils.tresp()
        resp.headers = h
        result = resp.get_cookies()
        assert len(result) == 1
        assert "cookiename" in result
        assert result["cookiename"][0] == ["cookievalue", odict.ODict()]

    def test_get_cookies_with_parameters(self):
        h = odict.ODictCaseless()
        h["Set-Cookie"] = [
            "cookiename=cookievalue;domain=example.com;expires=Wed Oct  21 16:29:41 2015;path=/; HttpOnly"]
        resp = tutils.tresp()
        resp.headers = h
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
        h = odict.ODictCaseless()
        h["Set-Cookie"] = [
            "cookiename=; Expires=Thu, 01-Jan-1970 00:00:01 GMT; path=/"
        ]
        resp = tutils.tresp()
        resp.headers = h
        result = resp.get_cookies()
        assert len(result) == 1
        assert "cookiename" in result
        assert result["cookiename"][0][0] == ""
        assert len(result["cookiename"][0][1]) == 2

    def test_get_cookies_twocookies(self):
        h = odict.ODictCaseless()
        h["Set-Cookie"] = ["cookiename=cookievalue", "othercookie=othervalue"]
        resp = tutils.tresp()
        resp.headers = h
        result = resp.get_cookies()
        assert len(result) == 2
        assert "cookiename" in result
        assert result["cookiename"][0] == ["cookievalue", odict.ODict()]
        assert "othercookie" in result
        assert result["othercookie"][0] == ["othervalue", odict.ODict()]

    def test_set_cookies(self):
        resp = tutils.tresp()
        v = resp.get_cookies()
        v.add("foo", ["bar", odict.ODictCaseless()])
        resp.set_cookies(v)

        v = resp.get_cookies()
        assert len(v) == 1
        assert v["foo"] == [["bar", odict.ODictCaseless()]]
