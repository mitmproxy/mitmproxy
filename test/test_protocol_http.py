from cStringIO import StringIO

from mock import MagicMock

from libmproxy.protocol.http import *
from netlib import odict

import tutils
import tservers


def test_HttpAuthenticationError():
    x = HttpAuthenticationError({"foo": "bar"})
    assert str(x)
    assert "foo" in x.headers


def test_stripped_chunked_encoding_no_content():
    """
    https://github.com/mitmproxy/mitmproxy/issues/186
    """
    r = tutils.tresp(content="")
    r.headers["Transfer-Encoding"] = ["chunked"]
    assert "Content-Length" in r._assemble_headers()

    r = tutils.treq(content="")
    r.headers["Transfer-Encoding"] = ["chunked"]
    assert "Content-Length" in r._assemble_headers()


class TestHTTPRequest:
    def test_asterisk_form_in(self):
        s = StringIO("OPTIONS * HTTP/1.1")
        f = tutils.tflow(req=None)
        f.request = HTTPRequest.from_stream(s)
        assert f.request.form_in == "relative"
        f.request.host = f.server_conn.address.host
        f.request.port = f.server_conn.address.port
        f.request.scheme = "http"
        assert f.request.assemble() == ("OPTIONS * HTTP/1.1\r\n"
                                        "Host: address:22\r\n"
                                        "Content-Length: 0\r\n\r\n")

    def test_relative_form_in(self):
        s = StringIO("GET /foo\xff HTTP/1.1")
        tutils.raises("Bad HTTP request line", HTTPRequest.from_stream, s)
        s = StringIO("GET /foo HTTP/1.1\r\nConnection: Upgrade\r\nUpgrade: h2c")
        r = HTTPRequest.from_stream(s)
        assert r.headers["Upgrade"] == ["h2c"]

        raw = r._assemble_headers()
        assert "Upgrade" not in raw
        assert "Host" not in raw

        r.url = "http://example.com/foo"

        raw = r._assemble_headers()
        assert "Host" in raw
        assert not "Host" in r.headers
        r.update_host_header()
        assert "Host" in r.headers

    def test_expect_header(self):
        s = StringIO(
            "GET / HTTP/1.1\r\nContent-Length: 3\r\nExpect: 100-continue\r\n\r\nfoobar")
        w = StringIO()
        r = HTTPRequest.from_stream(s, wfile=w)
        assert w.getvalue() == "HTTP/1.1 100 Continue\r\n\r\n"
        assert r.content == "foo"
        assert s.read(3) == "bar"

    def test_authority_form_in(self):
        s = StringIO("CONNECT oops-no-port.com HTTP/1.1")
        tutils.raises("Bad HTTP request line", HTTPRequest.from_stream, s)
        s = StringIO("CONNECT address:22 HTTP/1.1")
        r = HTTPRequest.from_stream(s)
        r.scheme, r.host, r.port = "http", "address", 22
        assert r.assemble() == ("CONNECT address:22 HTTP/1.1\r\n"
                                "Host: address:22\r\n"
                                "Content-Length: 0\r\n\r\n")
        assert r.pretty_url(False) == "address:22"

    def test_absolute_form_in(self):
        s = StringIO("GET oops-no-protocol.com HTTP/1.1")
        tutils.raises("Bad HTTP request line", HTTPRequest.from_stream, s)
        s = StringIO("GET http://address:22/ HTTP/1.1")
        r = HTTPRequest.from_stream(s)
        assert r.assemble(
        ) == "GET http://address:22/ HTTP/1.1\r\nHost: address:22\r\nContent-Length: 0\r\n\r\n"

    def test_http_options_relative_form_in(self):
        """
        Exercises fix for Issue #392.
        """
        s = StringIO("OPTIONS /secret/resource HTTP/1.1")
        r = HTTPRequest.from_stream(s)
        r.host = 'address'
        r.port = 80
        r.scheme = "http"
        assert r.assemble() == ("OPTIONS /secret/resource HTTP/1.1\r\n"
                                "Host: address\r\n"
                                "Content-Length: 0\r\n\r\n")

    def test_http_options_absolute_form_in(self):
        s = StringIO("OPTIONS http://address/secret/resource HTTP/1.1")
        r = HTTPRequest.from_stream(s)
        r.host = 'address'
        r.port = 80
        r.scheme = "http"
        assert r.assemble() == (
            "OPTIONS http://address:80/secret/resource HTTP/1.1\r\n"
            "Host: address\r\n"
            "Content-Length: 0\r\n\r\n")

    def test_assemble_unknown_form(self):
        r = tutils.treq()
        tutils.raises("Invalid request form", r.assemble, "antiauthority")

    def test_set_url(self):
        r = tutils.treq_absolute()
        r.url = "https://otheraddress:42/ORLY"
        assert r.scheme == "https"
        assert r.host == "otheraddress"
        assert r.port == 42
        assert r.path == "/ORLY"

    def test_repr(self):
        r = tutils.treq()
        assert repr(r)

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

    def test_get_form_for_urlencoded(self):
        r = tutils.treq()
        r.headers.add("content-type", "application/x-www-form-urlencoded")
        r.get_form_urlencoded = MagicMock()

        r.get_form()

        assert r.get_form_urlencoded.called

    def test_get_form_for_multipart(self):
        r = tutils.treq()
        r.headers.add("content-type", "multipart/form-data")
        r.get_form_multipart = MagicMock()

        r.get_form()

        assert r.get_form_multipart.called

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


class TestHTTPResponse:
    def test_read_from_stringio(self):
        _s = "HTTP/1.1 200 OK\r\n" \
             "Content-Length: 7\r\n" \
             "\r\n"\
             "content\r\n" \
             "HTTP/1.1 204 OK\r\n" \
             "\r\n"
        s = StringIO(_s)
        r = HTTPResponse.from_stream(s, "GET")
        assert r.code == 200
        assert r.content == "content"
        assert HTTPResponse.from_stream(s, "GET").code == 204

        s = StringIO(_s)
        # HEAD must not have content by spec. We should leave it on the pipe.
        r = HTTPResponse.from_stream(s, "HEAD")
        assert r.code == 200
        assert r.content == ""
        tutils.raises(
            "Invalid server response: 'content",
            HTTPResponse.from_stream, s, "GET"
        )

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


class TestHTTPFlow(object):
    def test_repr(self):
        f = tutils.tflow(resp=True, err=True)
        assert repr(f)


class TestInvalidRequests(tservers.HTTPProxTest):
    ssl = True

    def test_double_connect(self):
        p = self.pathoc()
        r = p.request("connect:'%s:%s'" % ("127.0.0.1", self.server2.port))
        assert r.status_code == 400
        assert "Must not CONNECT on already encrypted connection" in r.content

    def test_relative_request(self):
        p = self.pathoc_raw()
        p.connect()
        r = p.request("get:/p/200")
        assert r.status_code == 400
        assert "Invalid HTTP request form" in r.content
