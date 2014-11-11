from libmproxy.protocol.http import *
from cStringIO import StringIO
import tutils, tservers


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
        assert r.assemble() == "GET http://address:22/ HTTP/1.1\r\nHost: address:22\r\nContent-Length: 0\r\n\r\n"

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
        assert r.assemble() == ("OPTIONS http://address:80/secret/resource HTTP/1.1\r\n"
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
        r = HTTPResponse.from_stream(s, "HEAD")  # HEAD must not have content by spec. We should leave it on the pipe.
        assert r.code == 200
        assert r.content == ""
        tutils.raises("Invalid server response: 'content", HTTPResponse.from_stream, s, "GET")

    def test_repr(self):
        r = tutils.tresp()
        assert "unknown content type" in repr(r)
        r.headers["content-type"] = ["foo"]
        assert "foo" in repr(r)
        assert repr(tutils.tresp(content=CONTENT_MISSING))


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
