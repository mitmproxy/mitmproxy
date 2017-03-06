import os
import argparse
from unittest import mock
from OpenSSL import SSL
import pytest


from mitmproxy.tools import cmdline
from mitmproxy import options
from mitmproxy.proxy import ProxyConfig
from mitmproxy.proxy.server import DummyServer, ProxyServer, ConnectionHandler
from mitmproxy.proxy import config
from mitmproxy.test import tutils

from ..conftest import skip_windows


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
        opts = options.Options()
        cmdline.common_options(parser, opts)
        args = parser.parse_args(args=args)
        opts.merge(cmdline.get_common_options(args))
        pconf = config.ProxyConfig(opts)
        return parser, pconf

    def assert_noerr(self, *args):
        m, p = self.p(*args)
        assert p
        return p

    def test_simple(self):
        assert self.p()

    def test_cadir(self):
        with tutils.tmpdir() as cadir:
            self.assert_noerr("--cadir", cadir)

    def test_client_certs(self):
        with tutils.tmpdir() as cadir:
            self.assert_noerr("--client-certs", cadir)
            self.assert_noerr(
                "--client-certs",
                os.path.join(tutils.test_data.path("mitmproxy/data/clientcert"), "client.pem"))
            with pytest.raises(Exception, match="path does not exist"):
                self.p("--client-certs", "nonexistent")

    def test_certs(self):
        self.assert_noerr(
            "--cert",
            tutils.test_data.path("mitmproxy/data/testkey.pem"))
        with pytest.raises(Exception, match="does not exist"):
            self.p("--cert", "nonexistent")

    def test_insecure(self):
        p = self.assert_noerr("--ssl-insecure")
        assert p.openssl_verification_mode_server == SSL.VERIFY_NONE

    def test_upstream_trusted_cadir(self):
        expected_dir = "/path/to/a/ca/dir"
        p = self.assert_noerr("--ssl-verify-upstream-trusted-cadir", expected_dir)
        assert p.options.ssl_verify_upstream_trusted_cadir == expected_dir

    def test_upstream_trusted_ca(self):
        expected_file = "/path/to/a/cert/file"
        p = self.assert_noerr("--ssl-verify-upstream-trusted-ca", expected_file)
        assert p.options.ssl_verify_upstream_trusted_ca == expected_file


class TestProxyServer:

    @skip_windows
    def test_err(self):
        # binding to 0.0.0.0:1 works without special permissions on Windows
        conf = ProxyConfig(options.Options(listen_port=1))
        with pytest.raises(Exception, match="Error starting proxy server"):
            ProxyServer(conf)

    def test_err_2(self):
        conf = ProxyConfig(options.Options(listen_host="256.256.256.256"))
        with pytest.raises(Exception, match="Error starting proxy server"):
            ProxyServer(conf)


class TestDummyServer:

    def test_simple(self):
        d = DummyServer(None)
        d.set_channel(None)
        d.shutdown()


class TestConnectionHandler:

    def test_fatal_error(self, capsys):
        opts = options.Options()
        pconf = config.ProxyConfig(opts)

        channel = mock.Mock()

        def ask(_, x):
            raise RuntimeError

        channel.ask = ask
        c = ConnectionHandler(
            mock.MagicMock(),
            ("127.0.0.1", 8080),
            pconf,
            channel
        )
        c.handle()

        _, err = capsys.readouterr()
        assert "mitmproxy has crashed" in err
