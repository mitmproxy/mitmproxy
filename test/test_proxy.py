import threading, urllib, Queue, urllib2, cStringIO
import libpry
import serv, sslserv
from libmproxy import proxy, controller, utils, dump, script
import random

# Yes, the random ports are horrible. During development, sockets are often not
# properly closed during error conditions, which means you have to wait until
# you can re-bind to the same port. This is a pain in the ass, so we just pick
# a random port and keep moving.
PROXL_PORT = random.randint(10000, 20000)
HTTP_PORT = random.randint(20000, 30000)
HTTPS_PORT = random.randint(30000, 40000)


class TestMaster(controller.Master):
    def __init__(self, port, testq):
        serv = proxy.ProxyServer(port)
        controller.Master.__init__(self, serv)
        self.testq = testq
        self.log = []

    def clear(self):
        self.log = []

    def handle(self, m):
        self.log.append(m)
        m.ack()


class ProxyThread(threading.Thread):
    def __init__(self, port, testq):
        self.tmaster = TestMaster(port, testq)
        threading.Thread.__init__(self)

    def run(self):
        self.tmaster.run()

    def shutdown(self):
        self.tmaster.shutdown()


class ServerThread(threading.Thread):
    def __init__(self, server):
        self.server = server
        threading.Thread.__init__(self)

    def run(self):
        self.server.serve_forever()

    def shutdown(self):
        self.server.shutdown()


class _TestServers(libpry.TestContainer):
    def setUpAll(self):
        proxy.config = proxy.Config("data/testkey.pem")
        self.tqueue = Queue.Queue()
        # We don't make any concurrent requests, so we can access
        # the attributes on this object safely.
        self.proxthread = ProxyThread(PROXL_PORT, self.tqueue)
        self.threads = [
            ServerThread(serv.make(HTTP_PORT)),
            ServerThread(sslserv.make(HTTPS_PORT)),
            self.proxthread
        ]
        for i in self.threads:
            i.start()

    def setUp(self):
        self.proxthread.tmaster.clear()

    def tearDownAll(self):
        for i in self.threads:
            i.shutdown()


class _ProxTests(libpry.AutoTree):
    def log(self):
        pthread = self.findAttr("proxthread")
        return pthread.tmaster.log


class uSanity(_ProxTests):
    def test_http(self):
        """
            Just check that the HTTP server is running.
        """
        f = urllib.urlopen("http://127.0.0.1:%s"%HTTP_PORT)
        assert f.read()

    def test_https(self):
        """
            Just check that the HTTPS server is running.
        """
        f = urllib.urlopen("https://127.0.0.1:%s"%HTTPS_PORT)
        assert f.read()


class uProxy(_ProxTests):
    HOST = "127.0.0.1"
    def _get(self, host=HOST):
        r = urllib2.Request("http://%s:%s"%(host, HTTP_PORT))
        r.set_proxy("127.0.0.1:%s"%PROXL_PORT, "http")
        return urllib2.urlopen(r)

    def _sget(self, host=HOST):
        proxy_support = urllib2.ProxyHandler(
                            {"https" : "https://127.0.0.1:%s"%PROXL_PORT}
                        )
        opener = urllib2.build_opener(proxy_support)
        r = urllib2.Request("https://%s:%s"%(host, HTTPS_PORT))
        return opener.open(r)

    def test_http(self):
        f = self._get()
        assert f.code == 200
        assert f.read()
        f.close()
            
        l = self.log()
        assert l[0].address
        assert l[1].headers.has_key("host")
        assert l[2].code == 200

    def test_https(self):
        f = self._sget()
        assert f.code == 200
        assert f.read()
        f.close()

        l = self.log()
        assert l[0].address
        assert l[1].headers.has_key("host")
        assert l[2].code == 200

    # Disable these two for now: they take a long time.
    def _test_http_nonexistent(self):
        f = self._get("nonexistent")
        assert f.code == 200
        assert "Error" in f.read()

    def _test_https_nonexistent(self):
        f = self._sget("nonexistent")
        assert f.code == 200
        assert "Error" in f.read()



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
        c = proxy.ClientConnection(("addr", 2222))
        r = proxy.Request(c, "host", 22, "https", "GET", "/", h, "content")
        u = r.url()
        assert r.set_url(u)
        assert not r.set_url("")
        assert r.url() == u
        assert r.short()
        assert r.assemble()

    def test_getset_state(self):
        h = utils.Headers()
        h["test"] = ["test"]
        c = proxy.ClientConnection(("addr", 2222))
        r = proxy.Request(c, "host", 22, "https", "GET", "/", h, "content")
        state = r.get_state()
        assert proxy.Request.from_state(c, state) == r


class uResponse(libpry.AutoTree):
    def test_simple(self):
        h = utils.Headers()
        h["test"] = ["test"]
        c = proxy.ClientConnection(("addr", 2222))
        req = proxy.Request(c, "host", 22, "https", "GET", "/", h, "content")
        resp = proxy.Response(req, 200, "msg", h.copy(), "content")
        assert resp.short()
        assert resp.assemble()

    def test_getset_state(self):
        h = utils.Headers()
        h["test"] = ["test"]
        c = proxy.ClientConnection(("addr", 2222))
        r = proxy.Request(c, "host", 22, "https", "GET", "/", h, "content")
        req = proxy.Request(c, "host", 22, "https", "GET", "/", h, "content")
        resp = proxy.Response(req, 200, "HTTP", "msg", h.copy(), "content")

        state = resp.get_state()
        assert proxy.Response.from_state(req, state) == resp


class uError(libpry.AutoTree):
    def test_getset_state(self):
        e = proxy.Error(None, "Error")
        state = e.get_state()
        assert proxy.Error.from_state(state) == e

        assert e.copy()


class uProxyError(libpry.AutoTree):
    def test_simple(self):
        p = proxy.ProxyError(111, "msg")
        assert repr(p)



tests = [
    uProxyError(),
    uRequest(),
    uResponse(),
    uFileLike(),
    u_parse_request_line(),
    u_parse_url(),
    uError(),
    _TestServers(), [
        uSanity(),
        uProxy(),
    ]
]
