import cStringIO
import textwrap

from netlib import http, odict, tcp, tutils
from netlib.http import semantics, Headers
from netlib.http.http1 import HTTP1Protocol
from ... import tservers


class NoContentLengthHTTPHandler(tcp.BaseHandler):
    def handle(self):
        self.wfile.write("HTTP/1.1 200 OK\r\n\r\nbar\r\n\r\n")
        self.wfile.flush()


def mock_protocol(data=''):
    rfile = cStringIO.StringIO(data)
    wfile = cStringIO.StringIO()
    return HTTP1Protocol(rfile=rfile, wfile=wfile)


def match_http_string(data):
    return textwrap.dedent(data).strip().replace('\n', '\r\n')


def test_stripped_chunked_encoding_no_content():
    """
    https://github.com/mitmproxy/mitmproxy/issues/186
    """

    r = tutils.treq(content="")
    r.headers["Transfer-Encoding"] = "chunked"
    assert "Content-Length" in mock_protocol()._assemble_request_headers(r)

    r = tutils.tresp(content="")
    r.headers["Transfer-Encoding"] = "chunked"
    assert "Content-Length" in mock_protocol()._assemble_response_headers(r)


def test_has_chunked_encoding():
    headers = http.Headers()
    assert not HTTP1Protocol.has_chunked_encoding(headers)
    headers["transfer-encoding"] = "chunked"
    assert HTTP1Protocol.has_chunked_encoding(headers)


def test_read_chunked():
    headers = http.Headers()
    headers["transfer-encoding"] = "chunked"

    data = "1\r\na\r\n0\r\n"
    tutils.raises(
        "malformed chunked body",
        mock_protocol(data).read_http_body,
        headers, None, "GET", None, True
    )

    data = "1\r\na\r\n0\r\n\r\n"
    assert mock_protocol(data).read_http_body(headers, None, "GET", None, True) == "a"

    data = "\r\n\r\n1\r\na\r\n0\r\n\r\n"
    assert mock_protocol(data).read_http_body(headers, None, "GET", None, True) == "a"

    data = "\r\n"
    tutils.raises(
        "closed prematurely",
        mock_protocol(data).read_http_body,
        headers, None, "GET", None, True
    )

    data = "1\r\nfoo"
    tutils.raises(
        "malformed chunked body",
        mock_protocol(data).read_http_body,
        headers, None, "GET", None, True
    )

    data = "foo\r\nfoo"
    tutils.raises(
        http.HttpError,
        mock_protocol(data).read_http_body,
        headers, None, "GET", None, True
    )

    data = "5\r\naaaaa\r\n0\r\n\r\n"
    tutils.raises("too large", mock_protocol(data).read_http_body, headers, 2, "GET", None, True)


def test_connection_close():
    headers = Headers()
    assert HTTP1Protocol.connection_close((1, 0), headers)
    assert not HTTP1Protocol.connection_close((1, 1), headers)

    headers["connection"] = "keep-alive"
    assert not HTTP1Protocol.connection_close((1, 1), headers)

    headers["connection"] = "close"
    assert HTTP1Protocol.connection_close((1, 1), headers)


def test_read_http_body_request():
    headers = Headers()
    data = "testing"
    assert mock_protocol(data).read_http_body(headers, None, "GET", None, True) == ""


def test_read_http_body_response():
    headers = Headers()
    data = "testing"
    assert mock_protocol(data).read_http_body(headers, None, "GET", 200, False) == "testing"


def test_read_http_body():
    # test default case
    headers = Headers()
    headers["content-length"] = "7"
    data = "testing"
    assert mock_protocol(data).read_http_body(headers, None, "GET", 200, False) == "testing"

    # test content length: invalid header
    headers["content-length"] = "foo"
    data = "testing"
    tutils.raises(
        http.HttpError,
        mock_protocol(data).read_http_body,
        headers, None, "GET", 200, False
    )

    # test content length: invalid header #2
    headers["content-length"] = "-1"
    data = "testing"
    tutils.raises(
        http.HttpError,
        mock_protocol(data).read_http_body,
        headers, None, "GET", 200, False
    )

    # test content length: content length > actual content
    headers["content-length"] = "5"
    data = "testing"
    tutils.raises(
        http.HttpError,
        mock_protocol(data).read_http_body,
        headers, 4, "GET", 200, False
    )

    # test content length: content length < actual content
    data = "testing"
    assert len(mock_protocol(data).read_http_body(headers, None, "GET", 200, False)) == 5

    # test no content length: limit > actual content
    headers = Headers()
    data = "testing"
    assert len(mock_protocol(data).read_http_body(headers, 100, "GET", 200, False)) == 7

    # test no content length: limit < actual content
    data = "testing"
    tutils.raises(
        http.HttpError,
        mock_protocol(data).read_http_body,
        headers, 4, "GET", 200, False
    )

    # test chunked
    headers = Headers()
    headers["transfer-encoding"] = "chunked"
    data = "5\r\naaaaa\r\n0\r\n\r\n"
    assert mock_protocol(data).read_http_body(headers, 100, "GET", 200, False) == "aaaaa"


def test_expected_http_body_size():
    # gibber in the content-length field
    headers = Headers(content_length="foo")
    assert HTTP1Protocol.expected_http_body_size(headers, False, "GET", 200) is None
    # negative number in the content-length field
    headers = Headers(content_length="-7")
    assert HTTP1Protocol.expected_http_body_size(headers, False, "GET", 200) is None
    # explicit length
    headers = Headers(content_length="5")
    assert HTTP1Protocol.expected_http_body_size(headers, False, "GET", 200) == 5
    # no length
    headers = Headers()
    assert HTTP1Protocol.expected_http_body_size(headers, False, "GET", 200) == -1
    # no length request
    headers = Headers()
    assert HTTP1Protocol.expected_http_body_size(headers, True, "GET", None) == 0


def test_get_request_line():
    data = "\nfoo"
    p = mock_protocol(data)
    assert p._get_request_line() == "foo"
    assert not p._get_request_line()


def test_parse_http_protocol():
    assert HTTP1Protocol._parse_http_protocol("HTTP/1.1") == (1, 1)
    assert HTTP1Protocol._parse_http_protocol("HTTP/0.0") == (0, 0)
    assert not HTTP1Protocol._parse_http_protocol("HTTP/a.1")
    assert not HTTP1Protocol._parse_http_protocol("HTTP/1.a")
    assert not HTTP1Protocol._parse_http_protocol("foo/0.0")
    assert not HTTP1Protocol._parse_http_protocol("HTTP/x")


def test_parse_init_connect():
    assert HTTP1Protocol._parse_init_connect("CONNECT host.com:443 HTTP/1.0")
    assert not HTTP1Protocol._parse_init_connect("C\xfeONNECT host.com:443 HTTP/1.0")
    assert not HTTP1Protocol._parse_init_connect("CONNECT \0host.com:443 HTTP/1.0")
    assert not HTTP1Protocol._parse_init_connect("CONNECT host.com:444444 HTTP/1.0")
    assert not HTTP1Protocol._parse_init_connect("bogus")
    assert not HTTP1Protocol._parse_init_connect("GET host.com:443 HTTP/1.0")
    assert not HTTP1Protocol._parse_init_connect("CONNECT host.com443 HTTP/1.0")
    assert not HTTP1Protocol._parse_init_connect("CONNECT host.com:443 foo/1.0")
    assert not HTTP1Protocol._parse_init_connect("CONNECT host.com:foo HTTP/1.0")


def test_parse_init_proxy():
    u = "GET http://foo.com:8888/test HTTP/1.1"
    m, s, h, po, pa, httpversion = HTTP1Protocol._parse_init_proxy(u)
    assert m == "GET"
    assert s == "http"
    assert h == "foo.com"
    assert po == 8888
    assert pa == "/test"
    assert httpversion == (1, 1)

    u = "G\xfeET http://foo.com:8888/test HTTP/1.1"
    assert not HTTP1Protocol._parse_init_proxy(u)

    assert not HTTP1Protocol._parse_init_proxy("invalid")
    assert not HTTP1Protocol._parse_init_proxy("GET invalid HTTP/1.1")
    assert not HTTP1Protocol._parse_init_proxy("GET http://foo.com:8888/test foo/1.1")


def test_parse_init_http():
    u = "GET /test HTTP/1.1"
    m, u, httpversion = HTTP1Protocol._parse_init_http(u)
    assert m == "GET"
    assert u == "/test"
    assert httpversion == (1, 1)

    u = "G\xfeET /test HTTP/1.1"
    assert not HTTP1Protocol._parse_init_http(u)

    assert not HTTP1Protocol._parse_init_http("invalid")
    assert not HTTP1Protocol._parse_init_http("GET invalid HTTP/1.1")
    assert not HTTP1Protocol._parse_init_http("GET /test foo/1.1")
    assert not HTTP1Protocol._parse_init_http("GET /test\xc0 HTTP/1.1")


class TestReadHeaders:

    def _read(self, data, verbatim=False):
        if not verbatim:
            data = textwrap.dedent(data)
            data = data.strip()
        return mock_protocol(data).read_headers()

    def test_read_simple(self):
        data = """
            Header: one
            Header2: two
            \r\n
        """
        headers = self._read(data)
        assert headers.fields == [["Header", "one"], ["Header2", "two"]]

    def test_read_multi(self):
        data = """
            Header: one
            Header: two
            \r\n
        """
        headers = self._read(data)
        assert headers.fields == [["Header", "one"], ["Header", "two"]]

    def test_read_continued(self):
        data = """
            Header: one
            \ttwo
            Header2: three
            \r\n
        """
        headers = self._read(data)
        assert headers.fields == [["Header", "one\r\n two"], ["Header2", "three"]]

    def test_read_continued_err(self):
        data = "\tfoo: bar\r\n"
        assert self._read(data, True) is None

    def test_read_err(self):
        data = """
            foo
        """
        assert self._read(data) is None


class TestReadRequest(object):

    def tst(self, data, **kwargs):
        return mock_protocol(data).read_request(**kwargs)

    def test_invalid(self):
        tutils.raises(
            "bad http request",
            self.tst,
            "xxx"
        )
        tutils.raises(
            "bad http request line",
            self.tst,
            "get /\xff HTTP/1.1"
        )
        tutils.raises(
            "invalid headers",
            self.tst,
            "get / HTTP/1.1\r\nfoo"
        )
        tutils.raises(
            tcp.NetLibDisconnect,
            self.tst,
            "\r\n"
        )

    def test_empty(self):
        v = self.tst("", allow_empty=True)
        assert isinstance(v, semantics.EmptyRequest)

    def test_asterisk_form_in(self):
        v = self.tst("OPTIONS * HTTP/1.1")
        assert v.form_in == "relative"
        assert v.method == "OPTIONS"

    def test_absolute_form_in(self):
        tutils.raises(
            "Bad HTTP request line",
            self.tst,
            "GET oops-no-protocol.com HTTP/1.1"
        )
        v = self.tst("GET http://address:22/ HTTP/1.1")
        assert v.form_in == "absolute"
        assert v.port == 22
        assert v.host == "address"
        assert v.scheme == "http"

    def test_connect(self):
        tutils.raises(
            "Bad HTTP request line",
            self.tst,
            "CONNECT oops-no-port.com HTTP/1.1"
        )
        v = self.tst("CONNECT foo.com:443 HTTP/1.1")
        assert v.form_in == "authority"
        assert v.method == "CONNECT"
        assert v.port == 443
        assert v.host == "foo.com"

    def test_expect(self):
        data = "".join(
            "GET / HTTP/1.1\r\n"
            "Content-Length: 3\r\n"
            "Expect: 100-continue\r\n\r\n"
            "foobar"
        )

        p = mock_protocol(data)
        v = p.read_request()
        assert p.tcp_handler.wfile.getvalue() == "HTTP/1.1 100 Continue\r\n\r\n"
        assert v.body == "foo"
        assert p.tcp_handler.rfile.read(3) == "bar"


class TestReadResponse(object):
    def tst(self, data, method, body_size_limit, include_body=True):
        data = textwrap.dedent(data)
        return mock_protocol(data).read_response(
            method, body_size_limit, include_body=include_body
        )

    def test_errors(self):
        tutils.raises("server disconnect", self.tst, "", "GET", None)
        tutils.raises("invalid server response", self.tst, "foo", "GET", None)

    def test_simple(self):
        data = """
            HTTP/1.1 200
        """
        assert self.tst(data, "GET", None) == http.Response(
            (1, 1), 200, '', Headers(), ''
        )

    def test_simple_message(self):
        data = """
            HTTP/1.1 200 OK
        """
        assert self.tst(data, "GET", None) == http.Response(
            (1, 1), 200, 'OK', Headers(), ''
        )

    def test_invalid_http_version(self):
        data = """
            HTTP/x 200 OK
        """
        tutils.raises("invalid http version", self.tst, data, "GET", None)

    def test_invalid_status_code(self):
        data = """
            HTTP/1.1 xx OK
        """
        tutils.raises("invalid server response", self.tst, data, "GET", None)

    def test_valid_with_continue(self):
        data = """
            HTTP/1.1 100 CONTINUE

            HTTP/1.1 200 OK
        """
        assert self.tst(data, "GET", None) == http.Response(
            (1, 1), 100, 'CONTINUE', Headers(), ''
        )

    def test_simple_body(self):
        data = """
            HTTP/1.1 200 OK
            Content-Length: 3

            foo
        """
        assert self.tst(data, "GET", None).body == 'foo'
        assert self.tst(data, "HEAD", None).body == ''

    def test_invalid_headers(self):
        data = """
            HTTP/1.1 200 OK
            \tContent-Length: 3

            foo
        """
        tutils.raises("invalid headers", self.tst, data, "GET", None)

    def test_without_body(self):
        data = """
            HTTP/1.1 200 OK
            Content-Length: 3

            foo
        """
        assert self.tst(data, "GET", None, include_body=False).body is None


class TestReadResponseNoContentLength(tservers.ServerTestBase):
    handler = NoContentLengthHTTPHandler

    def test_no_content_length(self):
        c = tcp.TCPClient(("127.0.0.1", self.port))
        c.connect()
        resp = HTTP1Protocol(c).read_response("GET", None)
        assert resp.body == "bar\r\n\r\n"


class TestAssembleRequest(object):
    def test_simple(self):
        req = tutils.treq()
        b = HTTP1Protocol().assemble_request(req)
        assert b == match_http_string("""
            GET /path HTTP/1.1
            header: qvalue
            Host: address:22
            Content-Length: 7

            content""")

    def test_body_missing(self):
        req = tutils.treq(content=semantics.CONTENT_MISSING)
        tutils.raises(http.HttpError, HTTP1Protocol().assemble_request, req)

    def test_not_a_request(self):
        tutils.raises(AssertionError, HTTP1Protocol().assemble_request, 'foo')


class TestAssembleResponse(object):
    def test_simple(self):
        resp = tutils.tresp()
        b = HTTP1Protocol().assemble_response(resp)
        assert b == match_http_string("""
            HTTP/1.1 200 OK
            header_response: svalue
            Content-Length: 7

            message""")

    def test_body_missing(self):
        resp = tutils.tresp(content=semantics.CONTENT_MISSING)
        tutils.raises(http.HttpError, HTTP1Protocol().assemble_response, resp)

    def test_not_a_request(self):
        tutils.raises(AssertionError, HTTP1Protocol().assemble_response, 'foo')
