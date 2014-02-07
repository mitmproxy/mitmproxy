from libmproxy import proxy  # FIXME: Remove
from libmproxy.protocol.http import *
from cStringIO import StringIO
import tutils


def test_HttpAuthenticationError():
    x = HttpAuthenticationError({"foo": "bar"})
    assert str(x)
    assert "foo" in x.auth_headers


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
    def test_asterisk_form(self):
        s = StringIO("OPTIONS * HTTP/1.1")
        f = tutils.tflow_noreq()
        f.request = HTTPRequest.from_stream(s)
        assert f.request.form_in == "asterisk"
        x = f.request._assemble()
        assert f.request._assemble() == "OPTIONS * HTTP/1.1\r\nHost: address:22\r\n\r\n"

    def test_origin_form(self):
        s = StringIO("GET /foo\xff HTTP/1.1")
        tutils.raises("Bad HTTP request line", HTTPRequest.from_stream, s)

    def test_authority_form(self):
        s = StringIO("CONNECT oops-no-port.com HTTP/1.1")
        tutils.raises("Bad HTTP request line", HTTPRequest.from_stream, s)
        s = StringIO("CONNECT address:22 HTTP/1.1")
        r = HTTPRequest.from_stream(s)
        assert r._assemble() == "CONNECT address:22 HTTP/1.1\r\nHost: address:22\r\n\r\n"


    def test_absolute_form(self):
        s = StringIO("GET oops-no-protocol.com HTTP/1.1")
        tutils.raises("Bad HTTP request line", HTTPRequest.from_stream, s)
        s = StringIO("GET http://address:22/ HTTP/1.1")
        r = HTTPRequest.from_stream(s)
        assert r._assemble() == "GET http://address:22/ HTTP/1.1\r\nHost: address:22\r\n\r\n"

    def test_assemble_unknown_form(self):
        r = tutils.treq()
        tutils.raises("Invalid request form", r._assemble, "antiauthority")


    def test_set_url(self):
        r = tutils.treq_absolute()
        r.set_url("https://otheraddress:42/ORLY")
        assert r.scheme == "https"
        assert r.host == "otheraddress"
        assert r.port == 42
        assert r.path == "/ORLY"


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
