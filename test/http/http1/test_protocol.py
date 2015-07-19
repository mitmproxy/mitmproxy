import cStringIO
import textwrap
import binascii

from netlib import http, odict, tcp
from netlib.http.http1 import HTTP1Protocol
from ... import tutils, tservers


def mock_protocol(data='', chunked=False):
    class TCPHandlerMock(object):
        pass
    tcp_handler = TCPHandlerMock()
    tcp_handler.rfile = cStringIO.StringIO(data)
    tcp_handler.wfile = cStringIO.StringIO()
    return HTTP1Protocol(tcp_handler)



def test_has_chunked_encoding():
    h = odict.ODictCaseless()
    assert not HTTP1Protocol.has_chunked_encoding(h)
    h["transfer-encoding"] = ["chunked"]
    assert HTTP1Protocol.has_chunked_encoding(h)


def test_read_chunked():
    h = odict.ODictCaseless()
    h["transfer-encoding"] = ["chunked"]

    data = "1\r\na\r\n0\r\n"
    tutils.raises(
        "malformed chunked body",
        mock_protocol(data).read_http_body,
        h, None, "GET", None, True
    )

    data = "1\r\na\r\n0\r\n\r\n"
    assert mock_protocol(data).read_http_body(h, None, "GET", None, True) == "a"

    data = "\r\n\r\n1\r\na\r\n0\r\n\r\n"
    assert mock_protocol(data).read_http_body(h, None, "GET", None, True) == "a"

    data = "\r\n"
    tutils.raises(
        "closed prematurely",
        mock_protocol(data).read_http_body,
        h, None, "GET", None, True
    )

    data = "1\r\nfoo"
    tutils.raises(
        "malformed chunked body",
        mock_protocol(data).read_http_body,
        h, None, "GET", None, True
    )

    data = "foo\r\nfoo"
    tutils.raises(
        http.HttpError,
        mock_protocol(data).read_http_body,
        h, None, "GET", None, True
    )

    data = "5\r\naaaaa\r\n0\r\n\r\n"
    tutils.raises("too large", mock_protocol(data).read_http_body, h, 2, "GET", None, True)


def test_connection_close():
    h = odict.ODictCaseless()
    assert HTTP1Protocol.connection_close((1, 0), h)
    assert not HTTP1Protocol.connection_close((1, 1), h)

    h["connection"] = ["keep-alive"]
    assert not HTTP1Protocol.connection_close((1, 1), h)

    h["connection"] = ["close"]
    assert HTTP1Protocol.connection_close((1, 1), h)


def test_get_header_tokens():
    h = odict.ODictCaseless()
    assert http.get_header_tokens(h, "foo") == []
    h["foo"] = ["bar"]
    assert http.get_header_tokens(h, "foo") == ["bar"]
    h["foo"] = ["bar, voing"]
    assert http.get_header_tokens(h, "foo") == ["bar", "voing"]
    h["foo"] = ["bar, voing", "oink"]
    assert http.get_header_tokens(h, "foo") == ["bar", "voing", "oink"]


def test_read_http_body_request():
    h = odict.ODictCaseless()
    data = "testing"
    assert mock_protocol(data).read_http_body(h, None, "GET", None, True) == ""


def test_read_http_body_response():
    h = odict.ODictCaseless()
    data = "testing"
    assert mock_protocol(data, chunked=True).read_http_body(h, None, "GET", 200, False) == "testing"


def test_read_http_body():
    # test default case
    h = odict.ODictCaseless()
    h["content-length"] = [7]
    data = "testing"
    assert mock_protocol(data).read_http_body(h, None, "GET", 200, False) == "testing"

    # test content length: invalid header
    h["content-length"] = ["foo"]
    data = "testing"
    tutils.raises(
        http.HttpError,
        mock_protocol(data).read_http_body,
        h, None, "GET", 200, False
    )

    # test content length: invalid header #2
    h["content-length"] = [-1]
    data = "testing"
    tutils.raises(
        http.HttpError,
        mock_protocol(data).read_http_body,
        h, None, "GET", 200, False
    )

    # test content length: content length > actual content
    h["content-length"] = [5]
    data = "testing"
    tutils.raises(
        http.HttpError,
        mock_protocol(data).read_http_body,
        h, 4, "GET", 200, False
    )

    # test content length: content length < actual content
    data = "testing"
    assert len(mock_protocol(data).read_http_body(h, None, "GET", 200, False)) == 5

    # test no content length: limit > actual content
    h = odict.ODictCaseless()
    data = "testing"
    assert len(mock_protocol(data, chunked=True).read_http_body(h, 100, "GET", 200, False)) == 7

    # test no content length: limit < actual content
    data = "testing"
    tutils.raises(
        http.HttpError,
        mock_protocol(data, chunked=True).read_http_body,
        h, 4, "GET", 200, False
    )

    # test chunked
    h = odict.ODictCaseless()
    h["transfer-encoding"] = ["chunked"]
    data = "5\r\naaaaa\r\n0\r\n\r\n"
    assert mock_protocol(data, chunked=True).read_http_body(h, 100, "GET", 200, False) == "aaaaa"


def test_expected_http_body_size():
    # gibber in the content-length field
    h = odict.ODictCaseless()
    h["content-length"] = ["foo"]
    assert HTTP1Protocol.expected_http_body_size(h, False, "GET", 200) is None
    # negative number in the content-length field
    h = odict.ODictCaseless()
    h["content-length"] = ["-7"]
    assert HTTP1Protocol.expected_http_body_size(h, False, "GET", 200) is None
    # explicit length
    h = odict.ODictCaseless()
    h["content-length"] = ["5"]
    assert HTTP1Protocol.expected_http_body_size(h, False, "GET", 200) == 5
    # no length
    h = odict.ODictCaseless()
    assert HTTP1Protocol.expected_http_body_size(h, False, "GET", 200) == -1
    # no length request
    h = odict.ODictCaseless()
    assert HTTP1Protocol.expected_http_body_size(h, True, "GET", None) == 0


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
        h = self._read(data)
        assert h.lst == [["Header", "one"], ["Header2", "two"]]

    def test_read_multi(self):
        data = """
            Header: one
            Header: two
            \r\n
        """
        h = self._read(data)
        assert h.lst == [["Header", "one"], ["Header", "two"]]

    def test_read_continued(self):
        data = """
            Header: one
            \ttwo
            Header2: three
            \r\n
        """
        h = self._read(data)
        assert h.lst == [["Header", "one\r\n two"], ["Header2", "three"]]

    def test_read_continued_err(self):
        data = "\tfoo: bar\r\n"
        assert self._read(data, True) is None

    def test_read_err(self):
        data = """
            foo
        """
        assert self._read(data) is None


class NoContentLengthHTTPHandler(tcp.BaseHandler):

    def handle(self):
        self.wfile.write("HTTP/1.1 200 OK\r\n\r\nbar\r\n\r\n")
        self.wfile.flush()


class TestReadResponseNoContentLength(tservers.ServerTestBase):
    handler = NoContentLengthHTTPHandler

    def test_no_content_length(self):
        c = tcp.TCPClient(("127.0.0.1", self.port))
        c.connect()
        resp = HTTP1Protocol(c).read_response("GET", None)
        assert resp.body == "bar\r\n\r\n"


def test_read_response():
    def tst(data, method, limit, include_body=True):
        data = textwrap.dedent(data)
        return mock_protocol(data).read_response(
            method, limit, include_body=include_body
        )

    tutils.raises("server disconnect", tst, "", "GET", None)
    tutils.raises("invalid server response", tst, "foo", "GET", None)
    data = """
        HTTP/1.1 200 OK
    """
    assert tst(data, "GET", None) == http.Response(
        (1, 1), 200, 'OK', odict.ODictCaseless(), ''
    )
    data = """
        HTTP/1.1 200
    """
    assert tst(data, "GET", None) == http.Response(
        (1, 1), 200, '', odict.ODictCaseless(), ''
    )
    data = """
        HTTP/x 200 OK
    """
    tutils.raises("invalid http version", tst, data, "GET", None)
    data = """
        HTTP/1.1 xx OK
    """
    tutils.raises("invalid server response", tst, data, "GET", None)

    data = """
        HTTP/1.1 100 CONTINUE

        HTTP/1.1 200 OK
    """
    assert tst(data, "GET", None) == http.Response(
        (1, 1), 100, 'CONTINUE', odict.ODictCaseless(), ''
    )

    data = """
        HTTP/1.1 200 OK
        Content-Length: 3

        foo
    """
    assert tst(data, "GET", None).body == 'foo'
    assert tst(data, "HEAD", None).body == ''

    data = """
        HTTP/1.1 200 OK
        \tContent-Length: 3

        foo
    """
    tutils.raises("invalid headers", tst, data, "GET", None)

    data = """
        HTTP/1.1 200 OK
        Content-Length: 3

        foo
    """
    assert tst(data, "GET", None, include_body=False).body is None


def test_get_request_line():
    data = "\nfoo"
    p = mock_protocol(data)
    assert p._get_request_line() == "foo"
    assert not p._get_request_line()


class TestReadRequest():

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
