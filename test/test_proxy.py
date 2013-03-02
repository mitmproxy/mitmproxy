from libmproxy import proxy, flow
import tutils
from libpathod import test
from netlib import http, tcp
import mock


def test_proxy_error():
    p = proxy.ProxyError(111, "msg")
    assert str(p)


def test_app_registry():
    ar = proxy.AppRegistry()
    ar.add("foo", "domain", 80)

    r = tutils.treq()
    r.host = "domain"
    r.port = 80
    assert ar.get(r)

    r.port = 81
    assert not ar.get(r)

    r = tutils.treq()
    r.host = "domain2"
    r.port = 80
    assert not ar.get(r)
    r.headers["host"] = ["domain"]
    assert ar.get(r)


class TestServerConnection:
    def setUp(self):
        self.d = test.Daemon()

    def tearDown(self):
        self.d.shutdown()

    def test_simple(self):
        sc = proxy.ServerConnection(proxy.ProxyConfig(), "http", self.d.IFACE, self.d.port, "host.com")
        sc.connect()
        r = tutils.treq()
        r.path = "/p/200:da"
        sc.send(r)
        assert http.read_response(sc.rfile, r.method, 1000)
        assert self.d.last_log()

        r.content = flow.CONTENT_MISSING
        tutils.raises("incomplete request", sc.send, r)

        sc.terminate()

    def test_terminate_error(self):
        sc = proxy.ServerConnection(proxy.ProxyConfig(), "http", self.d.IFACE, self.d.port, "host.com")
        sc.connect()
        sc.connection = mock.Mock()
        sc.connection.close = mock.Mock(side_effect=IOError)
        sc.terminate()


class TestProcessOptions:
    def test_auth(self):
        parser = mock.MagicMock()
        



