import os
import mock
from OpenSSL import SSL

from mitmproxy import cmdline
from mitmproxy import options
from mitmproxy.proxy import ProxyConfig
from mitmproxy.models.connections import ServerConnection
from mitmproxy.proxy.server import DummyServer, ProxyServer, ConnectionHandler
from mitmproxy.proxy import config
from netlib.exceptions import TcpDisconnect
from pathod import test
from netlib.http import http1
from . import tutils


class TestServerConnection(object):

    def test_simple(self):
        self.d = test.Daemon()
        sc = ServerConnection((self.d.IFACE, self.d.port))
        sc.connect()
        f = tutils.tflow()
        f.server_conn = sc
        f.request.path = "/p/200:da"

        # use this protocol just to assemble - not for actual sending
        sc.wfile.write(http1.assemble_request(f.request))
        sc.wfile.flush()

        assert http1.read_response(sc.rfile, f.request, 1000)
        assert self.d.last_log()

        sc.finish()
        self.d.shutdown()

    def test_terminate_error(self):
        self.d = test.Daemon()
        sc = ServerConnection((self.d.IFACE, self.d.port))
        sc.connect()
        sc.connection = mock.Mock()
        sc.connection.recv = mock.Mock(return_value=False)
        sc.connection.flush = mock.Mock(side_effect=TcpDisconnect)
        sc.finish()
        self.d.shutdown()

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
        args = parser.parse_args(args=args)
        opts = cmdline.get_common_options(args)
        pconf = config.ProxyConfig(options.Options(**opts))
        return parser, pconf

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

    @mock.patch("mitmproxy.platform.resolver", None)
    def test_no_transparent(self):
        self.assert_err("transparent mode not supported", "-T")

    @mock.patch("mitmproxy.platform.resolver")
    def test_modes(self, _):
        self.assert_noerr("-R", "http://localhost")
        self.assert_err("expected one argument", "-R")
        self.assert_err("Invalid server specification", "-R", "reverse")

        self.assert_noerr("-T")

        self.assert_noerr("-U", "http://localhost")
        self.assert_err("expected one argument", "-U")
        self.assert_err("Invalid server specification", "-U", "upstream")

        self.assert_noerr("--upstream-auth", "test:test")
        self.assert_err("expected one argument", "--upstream-auth")
        self.assert_err(
            "Invalid upstream auth specification", "--upstream-auth", "test"
        )
        self.assert_err("mutually exclusive", "-R", "http://localhost", "-T")

    def test_socks_auth(self):
        self.assert_err(
            "Proxy Authentication not supported in SOCKS mode.",
            "--socks",
            "--nonanonymous"
        )

    def test_client_certs(self):
        with tutils.tmpdir() as cadir:
            self.assert_noerr("--client-certs", cadir)
            self.assert_noerr(
                "--client-certs",
                os.path.join(tutils.test_data.path("data/clientcert"), "client.pem"))
            self.assert_err(
                "path does not exist",
                "--client-certs",
                "nonexistent")

    def test_certs(self):
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

    def test_insecure(self):
        p = self.assert_noerr("--insecure")
        assert p.openssl_verification_mode_server == SSL.VERIFY_NONE

    def test_upstream_trusted_cadir(self):
        expected_dir = "/path/to/a/ca/dir"
        p = self.assert_noerr("--upstream-trusted-cadir", expected_dir)
        assert p.options.ssl_verify_upstream_trusted_cadir == expected_dir

    def test_upstream_trusted_ca(self):
        expected_file = "/path/to/a/cert/file"
        p = self.assert_noerr("--upstream-trusted-ca", expected_file)
        assert p.options.ssl_verify_upstream_trusted_ca == expected_file


class TestProxyServer:
    # binding to 0.0.0.0:1 works without special permissions on Windows

    @tutils.skip_windows
    def test_err(self):
        conf = ProxyConfig(
            options.Options(listen_port=1),
        )
        tutils.raises("error starting proxy server", ProxyServer, conf)

    def test_err_2(self):
        conf = ProxyConfig(
            options.Options(listen_host="invalidhost"),
        )
        tutils.raises("error starting proxy server", ProxyServer, conf)


class TestDummyServer:

    def test_simple(self):
        d = DummyServer(None)
        d.set_channel(None)
        d.shutdown()


class TestConnectionHandler:

    def test_fatal_error(self):
        config = mock.Mock()
        root_layer = mock.Mock()
        root_layer.side_effect = RuntimeError
        config.options.mode.return_value = root_layer
        channel = mock.Mock()

        def ask(_, x):
            return x
        channel.ask = ask
        c = ConnectionHandler(
            mock.MagicMock(),
            ("127.0.0.1", 8080),
            config,
            channel
        )
        with tutils.capture_stderr(c.handle) as output:
            assert "mitmproxy has crashed" in output
