import cStringIO, time, re
import libpry
from libmproxy import proxy, controller, utils, dump, script
import email.utils
import tutils


class u_read_chunked(libpry.AutoTree):
    def test_all(self):
        s = cStringIO.StringIO("1\r\na\r\n0\r\n")
        libpry.raises(IOError, proxy.read_chunked, s)

        s = cStringIO.StringIO("1\r\na\r\n0\r\n\r\n")
        assert proxy.read_chunked(s) == "a"

        s = cStringIO.StringIO("\r\n")
        libpry.raises(IOError, proxy.read_chunked, s)

        s = cStringIO.StringIO("1\r\nfoo")
        libpry.raises(IOError, proxy.read_chunked, s)



class u_parse_request_line(libpry.AutoTree):
    def test_simple(self):
        libpry.raises(proxy.ProxyError, proxy.parse_request_line, "")

        u = "GET ... HTTP/1.1"
        libpry.raises("invalid url", proxy.parse_request_line, u)

        u = "GET http://foo.com:8888/test HTTP/1.1"
        m, s, h, po, pa, minor = proxy.parse_request_line(u)
        assert m == "GET"
        assert s == "http"
        assert h == "foo.com"
        assert po == 8888
        assert pa == "/test"
        assert minor == 1

    def test_connect(self):
        u = "CONNECT host.com:443 HTTP/1.0"
        expected = ('CONNECT', None, 'host.com', 443, None, 0)
        ret = proxy.parse_request_line(u)
        assert expected == ret

    def test_inner(self):
        u = "GET / HTTP/1.1"
        assert proxy.parse_request_line(u) == ('GET', None, None, None, '/', 1)


class u_parse_url(libpry.AutoTree):
    def test_simple(self):
        assert not proxy.parse_url("")

        u = "http://foo.com:8888/test"
        s, h, po, pa = proxy.parse_url(u)
        assert s == "http"
        assert h == "foo.com"
        assert po == 8888
        assert pa == "/test"

        s, h, po, pa = proxy.parse_url("http://foo/bar")
        assert s == "http"
        assert h == "foo"
        assert po == 80
        assert pa == "/bar"

        s, h, po, pa = proxy.parse_url("http://foo")
        assert pa == "/"

        s, h, po, pa = proxy.parse_url("https://foo")
        assert po == 443


class uFileLike(libpry.AutoTree):
    def test_wrap(self):
        s = cStringIO.StringIO("foobar\nfoobar")
        s = proxy.FileLike(s)
        s.flush()
        assert s.readline() == "foobar\n"
        assert s.readline() == "foobar"
        # Test __getattr__
        assert s.isatty


class uRequest(libpry.AutoTree):
    def test_simple(self):
        h = utils.Headers()
        h["test"] = ["test"]
        c = proxy.ClientConnect(("addr", 2222))
        r = proxy.Request(c, "host", 22, "https", "GET", "/", h, "content")
        u = r.url()
        assert r.set_url(u)
        assert not r.set_url("")
        assert r.url() == u
        assert r.assemble()

        r2 = r.copy()
        assert r == r2

    def test_anticache(self):
        h = utils.Headers()
        r = proxy.Request(None, "host", 22, "https", "GET", "/", h, "content")
        h["if-modified-since"] = ["test"]
        h["if-none-match"] = ["test"]
        r.anticache()
        assert not "if-modified-since" in r.headers
        assert not "if-none-match" in r.headers

    def test_getset_state(self):
        h = utils.Headers()
        h["test"] = ["test"]
        c = proxy.ClientConnect(("addr", 2222))
        r = proxy.Request(c, "host", 22, "https", "GET", "/", h, "content")
        state = r.get_state()
        assert proxy.Request.from_state(state) == r

        r.client_conn = None
        state = r.get_state()
        assert proxy.Request.from_state(state) == r

        r2 = proxy.Request(c, "testing", 20, "http", "PUT", "/foo", h, "test")
        assert not r == r2
        r.load_state(r2.get_state())
        assert r == r2

        r2.client_conn = None
        r.load_state(r2.get_state())
        assert not r.client_conn

    def test_replace(self):
        r = tutils.treq()
        r.path = "path/foo"
        r.headers["Foo"] = ["fOo"]
        r.content = "afoob"
        assert r.replace("foo(?i)", "boo") == 4
        assert r.path == "path/boo"
        assert not "foo" in r.content
        assert r.headers["boo"] == ["boo"]


class uResponse(libpry.AutoTree):
    def test_simple(self):
        h = utils.Headers()
        h["test"] = ["test"]
        c = proxy.ClientConnect(("addr", 2222))
        req = proxy.Request(c, "host", 22, "https", "GET", "/", h, "content")
        resp = proxy.Response(req, 200, "msg", h.copy(), "content")
        assert resp.assemble()

        resp2 = resp.copy()
        assert resp2 == resp

    def test_refresh(self):
        r = tutils.tresp()
        n = time.time()
        r.headers["date"] = [email.utils.formatdate(n)]
        pre = r.headers["date"]
        r.refresh(n)
        assert pre == r.headers["date"]
        r.refresh(n+60)

        d = email.utils.parsedate_tz(r.headers["date"][0])
        d = email.utils.mktime_tz(d)
        # Weird that this is not exact...
        assert abs(60-(d-n)) <= 1

        r.headers["set-cookie"] = ["MOO=BAR; Expires=Tue, 08-Mar-2011 00:20:38 GMT; Path=foo.com; Secure"]
        r.refresh()

    def test_refresh_cookie(self):
        r = tutils.tresp()

        # Invalid expires format, sent to us by Reddit.
        c = "rfoo=bar; Domain=reddit.com; expires=Thu, 31 Dec 2037 23:59:59 GMT; Path=/"
        assert r._refresh_cookie(c, 60)

        c = "MOO=BAR; Expires=Tue, 08-Mar-2011 00:20:38 GMT; Path=foo.com; Secure"
        assert "00:21:38" in r._refresh_cookie(c, 60)


    def test_getset_state(self):
        h = utils.Headers()
        h["test"] = ["test"]
        c = proxy.ClientConnect(("addr", 2222))
        r = proxy.Request(c, "host", 22, "https", "GET", "/", h, "content")
        req = proxy.Request(c, "host", 22, "https", "GET", "/", h, "content")
        resp = proxy.Response(req, 200, "msg", h.copy(), "content")

        state = resp.get_state()
        assert proxy.Response.from_state(req, state) == resp

        resp2 = proxy.Response(req, 220, "foo", h.copy(), "test")
        assert not resp == resp2
        resp.load_state(resp2.get_state())
        assert resp == resp2

    def test_replace(self):
        r = tutils.tresp()
        r.headers["Foo"] = ["fOo"]
        r.content = "afoob"
        assert r.replace("foo(?i)", "boo") == 3
        assert not "foo" in r.content
        assert r.headers["boo"] == ["boo"]

    def test_decodeencode(self):
        r = tutils.tresp()
        r.headers["content-encoding"] = ["identity"]
        r.content = "falafel"
        r.decode()
        assert r.headers["content-encoding"] == ["identity"]
        assert r.content == "falafel"

        r = tutils.tresp()
        r.headers["content-encoding"] = ["identity"]
        r.content = "falafel"
        r.encode("identity")
        assert r.headers["content-encoding"] == ["identity"]
        assert r.content == "falafel"

        r = tutils.tresp()
        r.headers["content-encoding"] = ["identity"]
        r.content = "falafel"
        r.encode("gzip")
        assert r.headers["content-encoding"] == ["gzip"]
        assert r.content != "falafel"
        r.decode()
        assert r.headers["content-encoding"] == ["identity"]
        assert r.content == "falafel"


class uError(libpry.AutoTree):
    def test_getset_state(self):
        e = proxy.Error(None, "Error")
        state = e.get_state()
        assert proxy.Error.from_state(state) == e

        assert e.copy()

        e2 = proxy.Error(None, "bar")
        assert not e == e2
        e.load_state(e2.get_state())
        assert e == e2


        e3 = e.copy()
        assert e3 == e

    def test_replace(self):
        e = proxy.Error(None, "amoop")
        e.replace("moo", "bar")
        assert e.msg == "abarp"


class uProxyError(libpry.AutoTree):
    def test_simple(self):
        p = proxy.ProxyError(111, "msg")
        assert repr(p)


class uClientConnect(libpry.AutoTree):
    def test_state(self):
        c = proxy.ClientConnect(("a", 22))
        assert proxy.ClientConnect.from_state(c.get_state()) == c

        c2 = proxy.ClientConnect(("a", 25))
        assert not c == c2

        c.load_state(c2.get_state())
        assert c == c2


        c3 = c.copy()
        assert c3 == c


tests = [
    uProxyError(),
    uRequest(),
    uResponse(),
    uFileLike(),
    u_parse_request_line(),
    u_parse_url(),
    uError(),
    uClientConnect(),
    u_read_chunked(),
]
