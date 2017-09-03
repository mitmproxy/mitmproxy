from mitmproxy.net import tls
from mitmproxy.net.tcp import TCPClient
from test.mitmproxy.net.test_tcp import EchoHandler
from . import tservers


class TestSSLKeyLogger(tservers.ServerTestBase):
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
