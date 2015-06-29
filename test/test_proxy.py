import argparse
from libmproxy import cmdline
from libmproxy.proxy import ProxyConfig, process_proxy_options
from libmproxy.proxy.connection import ServerConnection
from libmproxy.proxy.primitives import ProxyError
from libmproxy.proxy.server import DummyServer, ProxyServer, ConnectionHandler
import tutils
from libpathod import test
from netlib import http, tcp
import mock

from OpenSSL import SSL


def test_proxy_error():
    p = ProxyError(111, "msg")
    assert str(p)


class TestServerConnection:
    def setUp(self):
        self.d = test.Daemon()

    def tearDown(self):
        self.d.shutdown()

    def test_simple(self):
        sc = ServerConnection((self.d.IFACE, self.d.port))
        sc.connect()
        f = tutils.tflow()
        f.server_conn = sc
        f.request.path = "/p/200:da"
        sc.send(f.request.assemble())
        assert http.read_response(sc.rfile, f.request.method, 1000)
        assert self.d.last_log()

        sc.finish()

    def test_terminate_error(self):
        sc = ServerConnection((self.d.IFACE, self.d.port))
        sc.connect()
        sc.connection = mock.Mock()
        sc.connection.recv = mock.Mock(return_value=False)
        sc.connection.flush = mock.Mock(side_effect=tcp.NetLibDisconnect)
        sc.finish()

    def test_repr(self):
        sc = tutils.tserver_conn()
        assert "address:22" in repr(sc)
        assert "ssl" not in repr(sc)
        sc.ssl_established = True
        assert "ssl" in repr(sc)
        sc.sni = "foo"
        assert "foo" in repr(sc)


class TestProcessProxyOptions:
    def p(self, *args):
        parser = tutils.MockParser()
        cmdline.common_options(parser)
        opts = parser.parse_args(args=args)
        return parser, process_proxy_options(parser, opts)

    def assert_err(self, err, *args):
        tutils.raises(err, self.p, *args)

    def assert_noerr(self, *args):
        m, p = self.p(*args)
        assert p
        return p

    def test_simple(self):
        assert self.p()

    def test_cadir(self):
        with tutils.tmpdir() as cadir:
            self.assert_noerr("--cadir", cadir)

    @mock.patch("libmproxy.platform.resolver", None)
    def test_no_transparent(self):
        self.assert_err("transparent mode not supported", "-T")

    @mock.patch("libmproxy.platform.resolver")
    def test_modes(self, _):
        self.assert_noerr("-R", "http://localhost")
        self.assert_err("expected one argument", "-R")
        self.assert_err("Invalid server specification", "-R", "reverse")

        self.assert_noerr("-T")

        self.assert_noerr("-U", "http://localhost")
        self.assert_err("expected one argument", "-U")
        self.assert_err("Invalid server specification", "-U", "upstream")

        self.assert_noerr("--spoof")
        self.assert_noerr("--ssl-spoof")

        self.assert_noerr("--spoofed-port", "443")
        self.assert_err("expected one argument", "--spoofed-port")

        self.assert_err("mutually exclusive", "-R", "http://localhost", "-T")

    def test_client_certs(self):
        with tutils.tmpdir() as cadir:
            self.assert_noerr("--client-certs", cadir)
            self.assert_err(
                "directory does not exist",
                "--client-certs",
                "nonexistent")

    def test_certs(self):
        with tutils.tmpdir() as cadir:
            self.assert_noerr(
                "--cert",
                tutils.test_data.path("data/testkey.pem"))
            self.assert_err("does not exist", "--cert", "nonexistent")

    def test_auth(self):
        p = self.assert_noerr("--nonanonymous")
        assert p.authenticator

        p = self.assert_noerr(
            "--htpasswd",
            tutils.test_data.path("data/htpasswd"))
        assert p.authenticator
        self.assert_err(
            "malformed htpasswd file",
            "--htpasswd",
            tutils.test_data.path("data/htpasswd.invalid"))

        p = self.assert_noerr("--singleuser", "test:test")
        assert p.authenticator
        self.assert_err(
            "invalid single-user specification",
            "--singleuser",
            "test")

    def test_verify_upstream_cert(self):
        p = self.assert_noerr("--verify-upstream-cert")
        assert p.openssl_verification_mode_server == SSL.VERIFY_PEER

    def test_upstream_trusted_cadir(self):
        expected_dir = "/path/to/a/ca/dir"
        p = self.assert_noerr("--upstream-trusted-cadir", expected_dir)
        assert p.openssl_trusted_cadir_server == expected_dir

    def test_upstream_trusted_ca(self):
        expected_file = "/path/to/a/cert/file"
        p = self.assert_noerr("--upstream-trusted-ca", expected_file)
        assert p.openssl_trusted_ca_server == expected_file


class TestProxyServer:
    # binding to 0.0.0.0:1 works without special permissions on Windows
    @tutils.SkipWindows
    def test_err(self):
        conf = ProxyConfig(
            port=1
        )
        tutils.raises("error starting proxy server", ProxyServer, conf)

    def test_err_2(self):
        conf = ProxyConfig(
            host="invalidhost"
        )
        tutils.raises("error starting proxy server", ProxyServer, conf)


class TestDummyServer:
    def test_simple(self):
        d = DummyServer(None)
        d.start_slave()
        d.shutdown()


class TestConnectionHandler:
    def test_fatal_error(self):
        config = mock.Mock()
        config.mode.get_upstream_server.side_effect = RuntimeError
        c = ConnectionHandler(
            config,
            mock.MagicMock(),
            ("127.0.0.1",
             8080),
            None,
            mock.MagicMock())
        with tutils.capture_stderr(c.handle) as output:
            assert "mitmproxy has crashed" in output
