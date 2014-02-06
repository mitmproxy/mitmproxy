import argparse
from libmproxy import proxy, flow, cmdline
import tutils
from libpathod import test
from netlib import http, tcp
import mock


def test_proxy_error():
    p = proxy.ProxyError(111, "msg")
    assert str(p)


class TestServerConnection:
    def setUp(self):
        self.d = test.Daemon()

    def tearDown(self):
        self.d.shutdown()

    def test_simple(self):
        sc = proxy.ServerConnection((self.d.IFACE, self.d.port), None)
        sc.connect()
        r = tutils.treq()
        r.flow.server_conn = sc
        r.path = "/p/200:da"
        sc.send(r._assemble())
        assert http.read_response(sc.rfile, r.method, 1000)
        assert self.d.last_log()

        sc.finish()

    def test_terminate_error(self):
        sc = proxy.ServerConnection((self.d.IFACE, self.d.port), None)
        sc.connect()
        sc.connection = mock.Mock()
        sc.connection.recv = mock.Mock(return_value=False)
        sc.connection.flush = mock.Mock(side_effect=tcp.NetLibDisconnect)
        sc.finish()


class MockParser:
    def __init__(self):
        self.err = None

    def error(self, e):
        self.err = e

    def __repr__(self):
        return "ParseError(%s)"%self.err


class TestProcessProxyOptions:
    def p(self, *args):
        parser = argparse.ArgumentParser()
        cmdline.common_options(parser)
        opts = parser.parse_args(args=args)
        m = MockParser()
        return m, proxy.process_proxy_options(m, opts)

    def assert_err(self, err, *args):
        m, p = self.p(*args)
        assert err.lower() in m.err.lower()

    def assert_noerr(self, *args):
        m, p = self.p(*args)
        assert p
        return p

    def test_simple(self):
        assert self.p()

    def test_cert(self):
        self.assert_noerr("--cert", tutils.test_data.path("data/testkey.pem"))
        self.assert_err("does not exist", "--cert", "nonexistent")

    def test_confdir(self):
        with tutils.tmpdir() as confdir:
            self.assert_noerr("--confdir", confdir)

    @mock.patch("libmproxy.platform.resolver", None)
    def test_no_transparent(self):
        self.assert_err("transparent mode not supported", "-T")

    @mock.patch("libmproxy.platform.resolver")
    def test_transparent_reverse(self, o):
        self.assert_err("can't set both", "-P", "reverse", "-T")
        self.assert_noerr("-T")
        assert o.call_count == 1
        self.assert_err("invalid reverse proxy", "-P", "reverse")
        self.assert_noerr("-P", "http://localhost")

    def test_certs(self):
        with tutils.tmpdir() as confdir:
            self.assert_noerr("--client-certs", confdir)
            self.assert_err("directory does not exist", "--client-certs", "nonexistent")

    def test_auth(self):
        p = self.assert_noerr("--nonanonymous")
        assert p.authenticator

        p = self.assert_noerr("--htpasswd", tutils.test_data.path("data/htpasswd"))
        assert p.authenticator
        self.assert_err("invalid htpasswd file", "--htpasswd", tutils.test_data.path("data/htpasswd.invalid"))

        p = self.assert_noerr("--singleuser", "test:test")
        assert p.authenticator
        self.assert_err("invalid single-user specification", "--singleuser", "test")


class TestProxyServer:
    @tutils.SkipWindows # binding to 0.0.0.0:1 works without special permissions on Windows
    def test_err(self):
        parser = argparse.ArgumentParser()
        cmdline.common_options(parser)
        opts = parser.parse_args(args=[])
        tutils.raises("error starting proxy server", proxy.ProxyServer, opts, 1)


class TestDummyServer:
    def test_simple(self):
        d = proxy.DummyServer(None)
        d.start_slave()
        d.shutdown()

