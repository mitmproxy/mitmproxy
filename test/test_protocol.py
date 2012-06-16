import cStringIO, textwrap
from libmproxy import protocol, flow
import tutils

def test_has_chunked_encoding():
    h = flow.ODictCaseless()
    assert not protocol.has_chunked_encoding(h)
    h["transfer-encoding"] = ["chunked"]
    assert protocol.has_chunked_encoding(h)


def test_read_chunked():
    s = cStringIO.StringIO("1\r\na\r\n0\r\n")
    tutils.raises(IOError, protocol.read_chunked, s, None)

    s = cStringIO.StringIO("1\r\na\r\n0\r\n\r\n")
    assert protocol.read_chunked(s, None) == "a"

    s = cStringIO.StringIO("\r\n")
    tutils.raises(IOError, protocol.read_chunked, s, None)

    s = cStringIO.StringIO("1\r\nfoo")
    tutils.raises(IOError, protocol.read_chunked, s, None)

    s = cStringIO.StringIO("foo\r\nfoo")
    tutils.raises(protocol.ProtocolError, protocol.read_chunked, s, None)


def test_request_connection_close():
    h = flow.ODictCaseless()
    assert protocol.request_connection_close((1, 0), h)
    assert not protocol.request_connection_close((1, 1), h)

    h["connection"] = ["keep-alive"]
    assert not protocol.request_connection_close((1, 1), h)


def test_read_http_body():
    h = flow.ODict()
    s = cStringIO.StringIO("testing")
    assert protocol.read_http_body(s, h, False, None) == ""

    h["content-length"] = ["foo"]
    s = cStringIO.StringIO("testing")
    tutils.raises(protocol.ProtocolError, protocol.read_http_body, s, h, False, None)

    h["content-length"] = [5]
    s = cStringIO.StringIO("testing")
    assert len(protocol.read_http_body(s, h, False, None)) == 5
    s = cStringIO.StringIO("testing")
    tutils.raises(protocol.ProtocolError, protocol.read_http_body, s, h, False, 4)

    h = flow.ODict()
    s = cStringIO.StringIO("testing")
    assert len(protocol.read_http_body(s, h, True, 4)) == 4
    s = cStringIO.StringIO("testing")
    assert len(protocol.read_http_body(s, h, True, 100)) == 7

def test_parse_http_protocol():
    assert protocol.parse_http_protocol("HTTP/1.1") == (1, 1)
    assert protocol.parse_http_protocol("HTTP/0.0") == (0, 0)
    assert not protocol.parse_http_protocol("foo/0.0")


def test_parse_init_connect():
    assert protocol.parse_init_connect("CONNECT host.com:443 HTTP/1.0")
    assert not protocol.parse_init_connect("bogus")
    assert not protocol.parse_init_connect("GET host.com:443 HTTP/1.0")
    assert not protocol.parse_init_connect("CONNECT host.com443 HTTP/1.0")
    assert not protocol.parse_init_connect("CONNECT host.com:443 foo/1.0")


def test_prase_init_proxy():
    u = "GET http://foo.com:8888/test HTTP/1.1"
    m, s, h, po, pa, httpversion = protocol.parse_init_proxy(u)
    assert m == "GET"
    assert s == "http"
    assert h == "foo.com"
    assert po == 8888
    assert pa == "/test"
    assert httpversion == (1, 1)

    assert not protocol.parse_init_proxy("invalid")
    assert not protocol.parse_init_proxy("GET invalid HTTP/1.1")
    assert not protocol.parse_init_proxy("GET http://foo.com:8888/test foo/1.1")


def test_parse_init_http():
    u = "GET /test HTTP/1.1"
    m, u, httpversion= protocol.parse_init_http(u)
    assert m == "GET"
    assert u == "/test"
    assert httpversion == (1, 1)

    assert not protocol.parse_init_http("invalid")
    assert not protocol.parse_init_http("GET invalid HTTP/1.1")
    assert not protocol.parse_init_http("GET /test foo/1.1")


class TestReadHeaders:
    def test_read_simple(self):
        data = """
            Header: one
            Header2: two
            \r\n
        """
        data = textwrap.dedent(data)
        data = data.strip()
        s = cStringIO.StringIO(data)
        headers = protocol.read_headers(s)
        assert headers["header"] == ["one"]
        assert headers["header2"] == ["two"]

    def test_read_multi(self):
        data = """
            Header: one
            Header: two
            \r\n
        """
        data = textwrap.dedent(data)
        data = data.strip()
        s = cStringIO.StringIO(data)
        headers = protocol.read_headers(s)
        assert headers["header"] == ["one", "two"]

    def test_read_continued(self):
        data = """
            Header: one
            \ttwo
            Header2: three
            \r\n
        """
        data = textwrap.dedent(data)
        data = data.strip()
        s = cStringIO.StringIO(data)
        headers = protocol.read_headers(s)
        assert headers["header"] == ['one\r\n two']


