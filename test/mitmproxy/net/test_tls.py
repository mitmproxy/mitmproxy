import pytest

from mitmproxy import exceptions
from mitmproxy.net import tls
from mitmproxy.net.tcp import TCPClient
from test.mitmproxy.net.test_tcp import EchoHandler
from . import tservers


class TestMasterSecretLogger(tservers.ServerTestBase):
    handler = EchoHandler
    ssl = dict(
        cipher_list="AES256-SHA"
    )

    def test_log(self, tmpdir):
        testval = b"echo!\n"
        _logfun = tls.log_master_secret

        logfile = str(tmpdir.join("foo", "bar", "logfile"))
        tls.log_master_secret = tls.MasterSecretLogger(logfile)

        c = TCPClient(("127.0.0.1", self.port))
        with c.connect():
            c.convert_to_ssl()
            c.wfile.write(testval)
            c.wfile.flush()
            assert c.rfile.readline() == testval
            c.finish()

            tls.log_master_secret.close()
            with open(logfile, "rb") as f:
                assert f.read().count(b"CLIENT_RANDOM") == 2

        tls.log_master_secret = _logfun

    def test_create_logfun(self):
        assert isinstance(
            tls.MasterSecretLogger.create_logfun("test"),
            tls.MasterSecretLogger)
        assert not tls.MasterSecretLogger.create_logfun(False)


class TestTLSInvalid:
    def test_invalid_ssl_method_should_fail(self):
        fake_ssl_method = 100500
        with pytest.raises(exceptions.TlsException):
            tls.create_client_context(method=fake_ssl_method)

    def test_alpn_error(self):
        with pytest.raises(exceptions.TlsException, match="must be a function"):
            tls.create_client_context(alpn_select_callback="foo")

        with pytest.raises(exceptions.TlsException, match="ALPN error"):
            tls.create_client_context(alpn_select="foo", alpn_select_callback="bar")
