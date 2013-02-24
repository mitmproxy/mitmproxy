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
        sc = proxy.ServerConnection(proxy.ProxyConfig(), self.d.IFACE, self.d.port)
        sc.connect("http", "host.com")
        r = tutils.treq()
        r.path = "/p/200:da"
        sc.send(r)
        assert http.read_response(sc.rfile, r.method, 1000)
        assert self.d.last_log()

        r.content = flow.CONTENT_MISSING
        tutils.raises("incomplete request", sc.send, r)

        sc.terminate()

    def test_terminate_error(self):
        sc = proxy.ServerConnection(proxy.ProxyConfig(), self.d.IFACE, self.d.port)
        sc.connect("http", "host.com")
        sc.connection = mock.Mock()
        sc.connection.close = mock.Mock(side_effect=IOError)
        sc.terminate()



def _dummysc(config, host, port):
    return mock.MagicMock(config=config, host=host, port=port)


def _errsc(config, host, port):
    m = mock.MagicMock(config=config, host=host, port=port)
    m.connect = mock.MagicMock(side_effect=tcp.NetLibError())
    return m


class TestServerConnectionPool:
    @mock.patch("libmproxy.proxy.ServerConnection", _dummysc)
    def test_pooling(self):
        p = proxy.ServerConnectionPool(proxy.ProxyConfig())
        c = p.get_connection("http", "localhost", 80, "localhost")
        c2 = p.get_connection("http", "localhost", 80, "localhost")
        assert c is c2
        c3 = p.get_connection("http", "foo", 80, "localhost")
        assert not c is c3

    @mock.patch("libmproxy.proxy.ServerConnection", _errsc)
    def test_connection_error(self):
        p = proxy.ServerConnectionPool(proxy.ProxyConfig())
        tutils.raises("502", p.get_connection, "http", "localhost", 80, "localhost")

