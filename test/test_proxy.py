import cStringIO, textwrap
from cStringIO import StringIO
import libpry
from libmproxy import proxy, flow
import tutils


def test_has_chunked_encoding():
    h = flow.ODictCaseless()
    assert not proxy.has_chunked_encoding(h)
    h["transfer-encoding"] = ["chunked"]
    assert proxy.has_chunked_encoding(h)


def test_read_chunked():
    s = cStringIO.StringIO("1\r\na\r\n0\r\n")
    tutils.raises(IOError, proxy.read_chunked, s, None)

    s = cStringIO.StringIO("1\r\na\r\n0\r\n\r\n")
    assert proxy.read_chunked(s, None) == "a"

    s = cStringIO.StringIO("\r\n")
    tutils.raises(IOError, proxy.read_chunked, s, None)

    s = cStringIO.StringIO("1\r\nfoo")
    tutils.raises(IOError, proxy.read_chunked, s, None)

    s = cStringIO.StringIO("foo\r\nfoo")
    tutils.raises(proxy.ProxyError, proxy.read_chunked, s, None)


def test_request_connection_close():
    h = flow.ODictCaseless()
    assert proxy.request_connection_close((1, 0), h)
    assert not proxy.request_connection_close((1, 1), h)

    h["connection"] = ["keep-alive"]
    assert not proxy.request_connection_close((1, 1), h)


def test_read_http_body():
    h = flow.ODict()
    s = cStringIO.StringIO("testing")
    assert proxy.read_http_body(s, h, False, None) == ""

    h["content-length"] = ["foo"]
    s = cStringIO.StringIO("testing")
    tutils.raises(proxy.ProxyError, proxy.read_http_body, s, h, False, None)

    h["content-length"] = [5]
    s = cStringIO.StringIO("testing")
    assert len(proxy.read_http_body(s, h, False, None)) == 5
    s = cStringIO.StringIO("testing")
    tutils.raises(proxy.ProxyError, proxy.read_http_body, s, h, False, 4)

    h = flow.ODict()
    s = cStringIO.StringIO("testing")
    assert len(proxy.read_http_body(s, h, True, 4)) == 4
    s = cStringIO.StringIO("testing")
    assert len(proxy.read_http_body(s, h, True, 100)) == 7


class TestProxyError:
    def test_simple(self):
        p = proxy.ProxyError(111, "msg")
        assert repr(p)


class TestReadHeaders:
    def test_read_simple(self):
        data = """
            Header: one
            Header2: two
            \r\n
        """
        data = textwrap.dedent(data)
        data = data.strip()
        s = StringIO(data)
        headers = proxy.read_headers(s)
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
        s = StringIO(data)
        headers = proxy.read_headers(s)
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
        s = StringIO(data)
        headers = proxy.read_headers(s)
        assert headers["header"] == ['one\r\n two']


def test_parse_http_protocol():
    assert proxy.parse_http_protocol("HTTP/1.1") == (1, 1)
    assert proxy.parse_http_protocol("HTTP/0.0") == (0, 0)
    assert not proxy.parse_http_protocol("foo/0.0")


def test_parse_init_connect():
    assert proxy.parse_init_connect("CONNECT host.com:443 HTTP/1.0")
    assert not proxy.parse_init_connect("bogus")
    assert not proxy.parse_init_connect("GET host.com:443 HTTP/1.0")
    assert not proxy.parse_init_connect("CONNECT host.com443 HTTP/1.0")
    assert not proxy.parse_init_connect("CONNECT host.com:443 foo/1.0")


def test_prase_init_proxy():
    u = "GET http://foo.com:8888/test HTTP/1.1"
    m, s, h, po, pa, httpversion = proxy.parse_init_proxy(u)
    assert m == "GET"
    assert s == "http"
    assert h == "foo.com"
    assert po == 8888
    assert pa == "/test"
    assert httpversion == (1, 1)

    assert not proxy.parse_init_proxy("invalid")
    assert not proxy.parse_init_proxy("GET invalid HTTP/1.1")
    assert not proxy.parse_init_proxy("GET http://foo.com:8888/test foo/1.1")


def test_parse_init_http():
    u = "GET /test HTTP/1.1"
    m, u, httpversion= proxy.parse_init_http(u)
    assert m == "GET"
    assert u == "/test"
    assert httpversion == (1, 1)

    assert not proxy.parse_init_http("invalid")
    assert not proxy.parse_init_http("GET invalid HTTP/1.1")
    assert not proxy.parse_init_http("GET /test foo/1.1")
