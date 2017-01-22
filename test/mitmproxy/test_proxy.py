from mitmproxy.test import tflow
import os
from unittest import mock
import argparse
from OpenSSL import SSL

from mitmproxy.tools import cmdline
from mitmproxy import options
from mitmproxy.proxy import ProxyConfig
from mitmproxy import connections
from mitmproxy.proxy.server import DummyServer, ProxyServer, ConnectionHandler
from mitmproxy.proxy import config
from mitmproxy import exceptions
from pathod import test
from mitmproxy.net.http import http1
from mitmproxy.test import tutils

from . import tutils as ttutils


class TestServerConnection:

    def test_simple(self):
        self.d = test.Daemon()
        sc = connections.ServerConnection((self.d.IFACE, self.d.port))
        sc.connect()
        f = tflow.tflow()
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
        sc = connections.ServerConnection((self.d.IFACE, self.d.port))
        sc.connect()
        sc.connection = mock.Mock()
        sc.connection.recv = mock.Mock(return_value=False)
        sc.connection.flush = mock.Mock(side_effect=exceptions.TcpDisconnect)
        sc.finish()
        self.d.shutdown()

    def test_repr(self):
        sc = tflow.tserver_conn()
        assert "address:22" in repr(sc)
        assert "ssl" not in repr(sc)
        sc.ssl_established = True
        assert "ssl" in repr(sc)
        sc.sni = "foo"
        assert "foo" in repr(sc)


class MockParser(argparse.ArgumentParser):

    """
    argparse.ArgumentParser sys.exits() by default.
    Make it more testable by throwing an exception instead.
    """

    def error(self, message):
        raise Exception(message)


class TestProcessProxyOptions:

    def p(self, *args):
        parser = MockParser()
        cmdline.common_options(parser)
        args = parser.parse_args(args=args)
        opts = options.Options()
        opts.merge(cmdline.get_common_options(args))
        pconf = config.ProxyConfig(opts)
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

    @mock.patch("mitmproxy.platform.original_addr", None)
    def test_no_transparent(self):
        self.assert_err("transparent mode not supported", "-T")

    @mock.patch("mitmproxy.platform.original_addr")
    def test_modes(self, _):
        self.assert_noerr("-R", "http://localhost")
        self.assert_err("expected one argument", "-R")
        self.assert_err("Invalid server specification", "-R", "reverse")

        self.assert_noerr("-T")

        self.assert_noerr("-U", "http://localhost")
        self.assert_err("Invalid server specification", "-U", "upstream")

        self.assert_noerr("--upstream-auth", "test:test")
        self.assert_err("expected one argument", "--upstream-auth")
        self.assert_err("mutually exclusive", "-R", "http://localhost", "-T")

    def test_client_certs(self):
        with tutils.tmpdir() as cadir:
            self.assert_noerr("--client-certs", cadir)
            self.assert_noerr(
                "--client-certs",
                os.path.join(tutils.test_data.path("mitmproxy/data/clientcert"), "client.pem"))
            self.assert_err(
                "path does not exist",
                "--client-certs",
                "nonexistent")

    def test_certs(self):
        self.assert_noerr(
            "--cert",
            tutils.test_data.path("mitmproxy/data/testkey.pem"))
        self.assert_err("does not exist", "--cert", "nonexistent")

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

    @ttutils.skip_windows
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
        with ttutils.capture_stderr(c.handle) as output:
            assert "mitmproxy has crashed" in output
