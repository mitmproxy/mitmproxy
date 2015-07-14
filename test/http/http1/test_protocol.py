import cStringIO
import textwrap
import binascii

from netlib import http, odict, tcp
from netlib.http.http1 import protocol
from ... import tutils, tservers


def test_has_chunked_encoding():
    h = odict.ODictCaseless()
    assert not protocol.has_chunked_encoding(h)
    h["transfer-encoding"] = ["chunked"]
    assert protocol.has_chunked_encoding(h)


def test_read_chunked():

    h = odict.ODictCaseless()
    h["transfer-encoding"] = ["chunked"]
    s = cStringIO.StringIO("1\r\na\r\n0\r\n")

    tutils.raises(
        "malformed chunked body",
        protocol.read_http_body,
        s, h, None, "GET", None, True
    )

    s = cStringIO.StringIO("1\r\na\r\n0\r\n\r\n")
    assert protocol.read_http_body(s, h, None, "GET", None, True) == "a"

    s = cStringIO.StringIO("\r\n\r\n1\r\na\r\n0\r\n\r\n")
    assert protocol.read_http_body(s, h, None, "GET", None, True) == "a"

    s = cStringIO.StringIO("\r\n")
    tutils.raises(
        "closed prematurely",
        protocol.read_http_body,
        s, h, None, "GET", None, True
    )

    s = cStringIO.StringIO("1\r\nfoo")
    tutils.raises(
        "malformed chunked body",
        protocol.read_http_body,
        s, h, None, "GET", None, True
    )

    s = cStringIO.StringIO("foo\r\nfoo")
    tutils.raises(
        protocol.HttpError,
        protocol.read_http_body,
        s, h, None, "GET", None, True
    )

    s = cStringIO.StringIO("5\r\naaaaa\r\n0\r\n\r\n")
    tutils.raises("too large", protocol.read_http_body, s, h, 2, "GET", None, True)


def test_connection_close():
    h = odict.ODictCaseless()
    assert protocol.connection_close((1, 0), h)
    assert not protocol.connection_close((1, 1), h)

    h["connection"] = ["keep-alive"]
    assert not protocol.connection_close((1, 1), h)

    h["connection"] = ["close"]
    assert protocol.connection_close((1, 1), h)


def test_get_header_tokens():
    h = odict.ODictCaseless()
    assert protocol.get_header_tokens(h, "foo") == []
    h["foo"] = ["bar"]
    assert protocol.get_header_tokens(h, "foo") == ["bar"]
    h["foo"] = ["bar, voing"]
    assert protocol.get_header_tokens(h, "foo") == ["bar", "voing"]
    h["foo"] = ["bar, voing", "oink"]
    assert protocol.get_header_tokens(h, "foo") == ["bar", "voing", "oink"]


def test_read_http_body_request():
    h = odict.ODictCaseless()
    r = cStringIO.StringIO("testing")
    assert protocol.read_http_body(r, h, None, "GET", None, True) == ""


def test_read_http_body_response():
    h = odict.ODictCaseless()
    s = tcp.Reader(cStringIO.StringIO("testing"))
    assert protocol.read_http_body(s, h, None, "GET", 200, False) == "testing"


def test_read_http_body():
    # test default case
    h = odict.ODictCaseless()
    h["content-length"] = [7]
    s = cStringIO.StringIO("testing")
    assert protocol.read_http_body(s, h, None, "GET", 200, False) == "testing"

    # test content length: invalid header
    h["content-length"] = ["foo"]
    s = cStringIO.StringIO("testing")
    tutils.raises(
        protocol.HttpError,
        protocol.read_http_body,
        s, h, None, "GET", 200, False
    )

    # test content length: invalid header #2
    h["content-length"] = [-1]
    s = cStringIO.StringIO("testing")
    tutils.raises(
        protocol.HttpError,
        protocol.read_http_body,
        s, h, None, "GET", 200, False
    )

    # test content length: content length > actual content
    h["content-length"] = [5]
    s = cStringIO.StringIO("testing")
    tutils.raises(
        protocol.HttpError,
        protocol.read_http_body,
        s, h, 4, "GET", 200, False
    )

    # test content length: content length < actual content
    s = cStringIO.StringIO("testing")
    assert len(protocol.read_http_body(s, h, None, "GET", 200, False)) == 5

    # test no content length: limit > actual content
    h = odict.ODictCaseless()
    s = tcp.Reader(cStringIO.StringIO("testing"))
    assert len(protocol.read_http_body(s, h, 100, "GET", 200, False)) == 7

    # test no content length: limit < actual content
    s = tcp.Reader(cStringIO.StringIO("testing"))
    tutils.raises(
        protocol.HttpError,
        protocol.read_http_body,
        s, h, 4, "GET", 200, False
    )

    # test chunked
    h = odict.ODictCaseless()
    h["transfer-encoding"] = ["chunked"]
    s = tcp.Reader(cStringIO.StringIO("5\r\naaaaa\r\n0\r\n\r\n"))
    assert protocol.read_http_body(s, h, 100, "GET", 200, False) == "aaaaa"


def test_expected_http_body_size():
    # gibber in the content-length field
    h = odict.ODictCaseless()
    h["content-length"] = ["foo"]
    assert protocol.expected_http_body_size(h, False, "GET", 200) is None
    # negative number in the content-length field
    h = odict.ODictCaseless()
    h["content-length"] = ["-7"]
    assert protocol.expected_http_body_size(h, False, "GET", 200) is None
    # explicit length
    h = odict.ODictCaseless()
    h["content-length"] = ["5"]
    assert protocol.expected_http_body_size(h, False, "GET", 200) == 5
    # no length
    h = odict.ODictCaseless()
    assert protocol.expected_http_body_size(h, False, "GET", 200) == -1
    # no length request
    h = odict.ODictCaseless()
    assert protocol.expected_http_body_size(h, True, "GET", None) == 0


def test_parse_http_protocol():
    assert protocol.parse_http_protocol("HTTP/1.1") == (1, 1)
    assert protocol.parse_http_protocol("HTTP/0.0") == (0, 0)
    assert not protocol.parse_http_protocol("HTTP/a.1")
    assert not protocol.parse_http_protocol("HTTP/1.a")
    assert not protocol.parse_http_protocol("foo/0.0")
    assert not protocol.parse_http_protocol("HTTP/x")


def test_parse_init_connect():
    assert protocol.parse_init_connect("CONNECT host.com:443 HTTP/1.0")
    assert not protocol.parse_init_connect("C\xfeONNECT host.com:443 HTTP/1.0")
    assert not protocol.parse_init_connect("CONNECT \0host.com:443 HTTP/1.0")
    assert not protocol.parse_init_connect("CONNECT host.com:444444 HTTP/1.0")
    assert not protocol.parse_init_connect("bogus")
    assert not protocol.parse_init_connect("GET host.com:443 HTTP/1.0")
    assert not protocol.parse_init_connect("CONNECT host.com443 HTTP/1.0")
    assert not protocol.parse_init_connect("CONNECT host.com:443 foo/1.0")
    assert not protocol.parse_init_connect("CONNECT host.com:foo HTTP/1.0")


def test_parse_init_proxy():
    u = "GET http://foo.com:8888/test HTTP/1.1"
    m, s, h, po, pa, httpversion = protocol.parse_init_proxy(u)
    assert m == "GET"
    assert s == "http"
    assert h == "foo.com"
    assert po == 8888
    assert pa == "/test"
    assert httpversion == (1, 1)

    u = "G\xfeET http://foo.com:8888/test HTTP/1.1"
    assert not protocol.parse_init_proxy(u)

    assert not protocol.parse_init_proxy("invalid")
    assert not protocol.parse_init_proxy("GET invalid HTTP/1.1")
    assert not protocol.parse_init_proxy("GET http://foo.com:8888/test foo/1.1")


def test_parse_init_http():
    u = "GET /test HTTP/1.1"
    m, u, httpversion = protocol.parse_init_http(u)
    assert m == "GET"
    assert u == "/test"
    assert httpversion == (1, 1)

    u = "G\xfeET /test HTTP/1.1"
    assert not protocol.parse_init_http(u)

    assert not protocol.parse_init_http("invalid")
    assert not protocol.parse_init_http("GET invalid HTTP/1.1")
    assert not protocol.parse_init_http("GET /test foo/1.1")
    assert not protocol.parse_init_http("GET /test\xc0 HTTP/1.1")


class TestReadHeaders:

    def _read(self, data, verbatim=False):
        if not verbatim:
            data = textwrap.dedent(data)
            data = data.strip()
        s = cStringIO.StringIO(data)
        return protocol.read_headers(s)

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
        resp = protocol.read_response(c.rfile, "GET", None)
        assert resp.content == "bar\r\n\r\n"


def test_read_response():
    def tst(data, method, limit, include_body=True):
        data = textwrap.dedent(data)
        r = cStringIO.StringIO(data)
        return protocol.read_response(
            r, method, limit, include_body=include_body
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
    assert tst(data, "GET", None).content == 'foo'
    assert tst(data, "HEAD", None).content == ''

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
    assert tst(data, "GET", None, include_body=False).content is None


def test_parse_http_basic_auth():
    vals = ("basic", "foo", "bar")
    assert protocol.parse_http_basic_auth(
        protocol.assemble_http_basic_auth(*vals)
    ) == vals
    assert not protocol.parse_http_basic_auth("")
    assert not protocol.parse_http_basic_auth("foo bar")
    v = "basic " + binascii.b2a_base64("foo")
    assert not protocol.parse_http_basic_auth(v)


def test_get_request_line():
    r = cStringIO.StringIO("\nfoo")
    assert protocol.get_request_line(r) == "foo"
    assert not protocol.get_request_line(r)


class TestReadRequest():

    def tst(self, data, **kwargs):
        r = cStringIO.StringIO(data)
        return protocol.read_request(r, **kwargs)

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
        w = cStringIO.StringIO()
        r = cStringIO.StringIO(
            "GET / HTTP/1.1\r\n"
            "Content-Length: 3\r\n"
            "Expect: 100-continue\r\n\r\n"
            "foobar",
        )
        v = protocol.read_request(r, wfile=w)
        assert w.getvalue() == "HTTP/1.1 100 Continue\r\n\r\n"
        assert v.content == "foo"
        assert r.read(3) == "bar"
