import argparse
from unittest import mock
from OpenSSL import SSL
import pytest

from pathod import pathoc
from mitmproxy import exceptions
from mitmproxy.tools import cmdline
from mitmproxy.tools import main
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
        pconf = main.process_options(parser, opts, args)
        return parser, pconf

    def assert_noerr(self, *args):
        m, p = self.p(*args)
        assert p
        return p

    def test_simple(self):
        assert self.p()

    def test_certs(self):
        self.assert_noerr(
            "--cert",
            tutils.test_data.path("mitmproxy/data/testkey.pem"))
        with pytest.raises(Exception, match="does not exist"):
            self.p("--cert", "nonexistent")

    def test_insecure(self):
        p = self.assert_noerr("--ssl-insecure")
        assert p.openssl_verification_mode_server == SSL.VERIFY_NONE


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

    def check_proxy_for_mode(self, mode):
        """
        Checks that we get correct log message in specific mode
        """
        warning_triggered = False
        log_msg = "The proxy shall not connect to itself."

        opts = options.Options(mode=mode)
        pconf = config.ProxyConfig(opts)

        channel = mock.Mock()

        def tell(mtype, m):
            if m.level == "warn":
                assert log_msg in m.msg
                nonlocal warning_triggered
                warning_triggered = True

        channel.tell = tell

        c = ConnectionHandler(
            mock.MagicMock(),
            ("127.0.0.1", 8080),
            pconf,
            channel
        )
        c.handle()

        p = pathoc.Pathoc(("127.0.0.1", 8080))
        try:
            p.connect()
        except exceptions.TcpException:
            pass

        assert warning_triggered

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

    def test_selfconnected_reverse_proxy(self):
        reverse_mode = "reverse:http://127.0.0.1:8080"
        self.check_proxy_for_mode(reverse_mode)

    def test_selfconnected_upstream_proxy(self):
        upstream_mode = "upstream:http://127.0.0.1:8080"
        self.check_proxy_for_mode(upstream_mode)
