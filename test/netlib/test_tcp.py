from io import BytesIO
from six.moves import queue
import time
import socket
import random
import os
import threading
import mock

from OpenSSL import SSL
import OpenSSL

from netlib import tcp, certutils, tutils
from netlib.exceptions import InvalidCertificateException, TcpReadIncomplete, TlsException, \
    TcpTimeout, TcpDisconnect, TcpException, NetlibException

from . import tservers

class EchoHandler(tcp.BaseHandler):
    sni = None

    def handle_sni(self, connection):
        self.sni = connection.get_servername()

    def handle(self):
        v = self.rfile.readline()
        self.wfile.write(v)
        self.wfile.flush()


class ClientCipherListHandler(tcp.BaseHandler):
    sni = None

    def handle(self):
        self.wfile.write("%s" % self.connection.get_cipher_list())
        self.wfile.flush()


class HangHandler(tcp.BaseHandler):

    def handle(self):
        while True:
            time.sleep(1)


class ALPNHandler(tcp.BaseHandler):
    sni = None

    def handle(self):
        alp = self.get_alpn_proto_negotiated()
        if alp:
            self.wfile.write(alp)
        else:
            self.wfile.write(b"NONE")
        self.wfile.flush()


class TestServer(tservers.ServerTestBase):
    handler = EchoHandler

    def test_echo(self):
        testval = b"echo!\n"
        c = tcp.TCPClient(("127.0.0.1", self.port))
        c.connect()
        c.wfile.write(testval)
        c.wfile.flush()
        assert c.rfile.readline() == testval

    def test_thread_start_error(self):
        with mock.patch.object(threading.Thread, "start", side_effect=threading.ThreadError("nonewthread")) as m:
            c = tcp.TCPClient(("127.0.0.1", self.port))
            c.connect()
            assert not c.rfile.read(1)
            assert m.called
            assert "nonewthread" in self.q.get_nowait()
        self.test_echo()


class TestServerBind(tservers.ServerTestBase):

    class handler(tcp.BaseHandler):

        def handle(self):
            self.wfile.write(str(self.connection.getpeername()).encode())
            self.wfile.flush()

    def test_bind(self):
        """ Test to bind to a given random port. Try again if the random port turned out to be blocked. """
        for i in range(20):
            random_port = random.randrange(1024, 65535)
            try:
                c = tcp.TCPClient(
                    ("127.0.0.1", self.port), source_address=(
                        "127.0.0.1", random_port))
                c.connect()
                assert c.rfile.readline() == str(("127.0.0.1", random_port)).encode()
                return
            except TcpException:  # port probably already in use
                pass


class TestServerIPv6(tservers.ServerTestBase):
    handler = EchoHandler
    addr = tcp.Address(("localhost", 0), use_ipv6=True)

    def test_echo(self):
        testval = b"echo!\n"
        c = tcp.TCPClient(tcp.Address(("::1", self.port), use_ipv6=True))
        c.connect()
        c.wfile.write(testval)
        c.wfile.flush()
        assert c.rfile.readline() == testval


class TestEcho(tservers.ServerTestBase):
    handler = EchoHandler

    def test_echo(self):
        testval = b"echo!\n"
        c = tcp.TCPClient(("127.0.0.1", self.port))
        c.connect()
        c.wfile.write(testval)
        c.wfile.flush()
        assert c.rfile.readline() == testval


class HardDisconnectHandler(tcp.BaseHandler):

    def handle(self):
        self.connection.close()


class TestFinishFail(tservers.ServerTestBase):

    """
        This tests a difficult-to-trigger exception in the .finish() method of
        the handler.
    """
    handler = EchoHandler

    def test_disconnect_in_finish(self):
        c = tcp.TCPClient(("127.0.0.1", self.port))
        c.connect()
        c.wfile.write(b"foo\n")
        c.wfile.flush = mock.Mock(side_effect=TcpDisconnect)
        c.finish()


class TestServerSSL(tservers.ServerTestBase):
    handler = EchoHandler
    ssl = dict(
        cipher_list="AES256-SHA",
        chain_file=tutils.test_data.path("data/server.crt")
    )

    def test_echo(self):
        c = tcp.TCPClient(("127.0.0.1", self.port))
        c.connect()
        c.convert_to_ssl(sni=b"foo.com", options=SSL.OP_ALL)
        testval = b"echo!\n"
        c.wfile.write(testval)
        c.wfile.flush()
        assert c.rfile.readline() == testval

    def test_get_current_cipher(self):
        c = tcp.TCPClient(("127.0.0.1", self.port))
        c.connect()
        assert not c.get_current_cipher()
        c.convert_to_ssl(sni=b"foo.com")
        ret = c.get_current_cipher()
        assert ret
        assert "AES" in ret[0]


class TestSSLv3Only(tservers.ServerTestBase):
    handler = EchoHandler
    ssl = dict(
        request_client_cert=False,
        v3_only=True
    )

    def test_failure(self):
        c = tcp.TCPClient(("127.0.0.1", self.port))
        c.connect()
        tutils.raises(TlsException, c.convert_to_ssl, sni=b"foo.com")


class TestSSLUpstreamCertVerificationWBadServerCert(tservers.ServerTestBase):
    handler = EchoHandler

    ssl = dict(
        cert=tutils.test_data.path("data/verificationcerts/self-signed.crt"),
        key=tutils.test_data.path("data/verificationcerts/self-signed.key")
    )

    def test_mode_default_should_pass(self):
        c = tcp.TCPClient(("127.0.0.1", self.port))
        c.connect()

        c.convert_to_ssl()

        # Verification errors should be saved even if connection isn't aborted
        # aborted
        assert c.ssl_verification_error is not None

        testval = b"echo!\n"
        c.wfile.write(testval)
        c.wfile.flush()
        assert c.rfile.readline() == testval

    def test_mode_none_should_pass(self):
        c = tcp.TCPClient(("127.0.0.1", self.port))
        c.connect()

        c.convert_to_ssl(verify_options=SSL.VERIFY_NONE)

        # Verification errors should be saved even if connection isn't aborted
        assert c.ssl_verification_error is not None

        testval = b"echo!\n"
        c.wfile.write(testval)
        c.wfile.flush()
        assert c.rfile.readline() == testval

    def test_mode_strict_should_fail(self):
        c = tcp.TCPClient(("127.0.0.1", self.port))
        c.connect()

        with tutils.raises(InvalidCertificateException):
            c.convert_to_ssl(
                sni=b"example.mitmproxy.org",
                verify_options=SSL.VERIFY_PEER,
                ca_pemfile=tutils.test_data.path("data/verificationcerts/trusted-root.crt")
            )

        assert c.ssl_verification_error is not None

        # Unknown issuing certificate authority for first certificate
        assert c.ssl_verification_error['errno'] == 18
        assert c.ssl_verification_error['depth'] == 0


class TestSSLUpstreamCertVerificationWBadHostname(tservers.ServerTestBase):
    handler = EchoHandler

    ssl = dict(
        cert=tutils.test_data.path("data/verificationcerts/trusted-leaf.crt"),
        key=tutils.test_data.path("data/verificationcerts/trusted-leaf.key")
    )

    def test_should_fail_without_sni(self):
        c = tcp.TCPClient(("127.0.0.1", self.port))
        c.connect()

        with tutils.raises(TlsException):
            c.convert_to_ssl(
                verify_options=SSL.VERIFY_PEER,
                ca_pemfile=tutils.test_data.path("data/verificationcerts/trusted-root.crt")
            )

    def test_should_fail(self):
        c = tcp.TCPClient(("127.0.0.1", self.port))
        c.connect()

        with tutils.raises(InvalidCertificateException):
            c.convert_to_ssl(
                sni=b"mitmproxy.org",
                verify_options=SSL.VERIFY_PEER,
                ca_pemfile=tutils.test_data.path("data/verificationcerts/trusted-root.crt")
            )

        assert c.ssl_verification_error is not None


class TestSSLUpstreamCertVerificationWValidCertChain(tservers.ServerTestBase):
    handler = EchoHandler

    ssl = dict(
        cert=tutils.test_data.path("data/verificationcerts/trusted-leaf.crt"),
        key=tutils.test_data.path("data/verificationcerts/trusted-leaf.key")
    )

    def test_mode_strict_w_pemfile_should_pass(self):
        c = tcp.TCPClient(("127.0.0.1", self.port))
        c.connect()

        c.convert_to_ssl(
            sni=b"example.mitmproxy.org",
            verify_options=SSL.VERIFY_PEER,
            ca_pemfile=tutils.test_data.path("data/verificationcerts/trusted-root.crt")
        )

        assert c.ssl_verification_error is None

        testval = b"echo!\n"
        c.wfile.write(testval)
        c.wfile.flush()
        assert c.rfile.readline() == testval

    def test_mode_strict_w_cadir_should_pass(self):
        c = tcp.TCPClient(("127.0.0.1", self.port))
        c.connect()

        c.convert_to_ssl(
            sni=b"example.mitmproxy.org",
            verify_options=SSL.VERIFY_PEER,
            ca_path=tutils.test_data.path("data/verificationcerts/")
        )

        assert c.ssl_verification_error is None

        testval = b"echo!\n"
        c.wfile.write(testval)
        c.wfile.flush()
        assert c.rfile.readline() == testval


class TestSSLClientCert(tservers.ServerTestBase):

    class handler(tcp.BaseHandler):
        sni = None

        def handle_sni(self, connection):
            self.sni = connection.get_servername()

        def handle(self):
            self.wfile.write(b"%d\n" % self.clientcert.serial)
            self.wfile.flush()

    ssl = dict(
        request_client_cert=True,
        v3_only=False
    )

    def test_clientcert(self):
        c = tcp.TCPClient(("127.0.0.1", self.port))
        c.connect()
        c.convert_to_ssl(
            cert=tutils.test_data.path("data/clientcert/client.pem"))
        assert c.rfile.readline().strip() == b"1"

    def test_clientcert_err(self):
        c = tcp.TCPClient(("127.0.0.1", self.port))
        c.connect()
        tutils.raises(
            TlsException,
            c.convert_to_ssl,
            cert=tutils.test_data.path("data/clientcert/make")
        )


class TestSNI(tservers.ServerTestBase):

    class handler(tcp.BaseHandler):
        sni = None

        def handle_sni(self, connection):
            self.sni = connection.get_servername()

        def handle(self):
            self.wfile.write(self.sni)
            self.wfile.flush()

    ssl = True

    def test_echo(self):
        c = tcp.TCPClient(("127.0.0.1", self.port))
        c.connect()
        c.convert_to_ssl(sni=b"foo.com")
        assert c.sni == b"foo.com"
        assert c.rfile.readline() == b"foo.com"


class TestServerCipherList(tservers.ServerTestBase):
    handler = ClientCipherListHandler
    ssl = dict(
        cipher_list='RC4-SHA'
    )

    def test_echo(self):
        c = tcp.TCPClient(("127.0.0.1", self.port))
        c.connect()
        c.convert_to_ssl(sni=b"foo.com")
        assert c.rfile.readline() == b"['RC4-SHA']"


class TestServerCurrentCipher(tservers.ServerTestBase):

    class handler(tcp.BaseHandler):
        sni = None

        def handle(self):
            self.wfile.write(str(self.get_current_cipher()).encode())
            self.wfile.flush()

    ssl = dict(
        cipher_list='RC4-SHA'
    )

    def test_echo(self):
        c = tcp.TCPClient(("127.0.0.1", self.port))
        c.connect()
        c.convert_to_ssl(sni=b"foo.com")
        assert b"RC4-SHA" in c.rfile.readline()


class TestServerCipherListError(tservers.ServerTestBase):
    handler = ClientCipherListHandler
    ssl = dict(
        cipher_list='bogus'
    )

    def test_echo(self):
        c = tcp.TCPClient(("127.0.0.1", self.port))
        c.connect()
        tutils.raises("handshake error", c.convert_to_ssl, sni=b"foo.com")


class TestClientCipherListError(tservers.ServerTestBase):
    handler = ClientCipherListHandler
    ssl = dict(
        cipher_list='RC4-SHA'
    )

    def test_echo(self):
        c = tcp.TCPClient(("127.0.0.1", self.port))
        c.connect()
        tutils.raises(
            "cipher specification",
            c.convert_to_ssl,
            sni=b"foo.com",
            cipher_list="bogus")


class TestSSLDisconnect(tservers.ServerTestBase):

    class handler(tcp.BaseHandler):

        def handle(self):
            self.finish()

    ssl = True

    def test_echo(self):
        c = tcp.TCPClient(("127.0.0.1", self.port))
        c.connect()
        c.convert_to_ssl()
        # Excercise SSL.ZeroReturnError
        c.rfile.read(10)
        c.close()
        tutils.raises(TcpDisconnect, c.wfile.write, b"foo")
        tutils.raises(queue.Empty, self.q.get_nowait)


class TestSSLHardDisconnect(tservers.ServerTestBase):
    handler = HardDisconnectHandler
    ssl = True

    def test_echo(self):
        c = tcp.TCPClient(("127.0.0.1", self.port))
        c.connect()
        c.convert_to_ssl()
        # Exercise SSL.SysCallError
        c.rfile.read(10)
        c.close()
        tutils.raises(TcpDisconnect, c.wfile.write, b"foo")


class TestDisconnect(tservers.ServerTestBase):

    def test_echo(self):
        c = tcp.TCPClient(("127.0.0.1", self.port))
        c.connect()
        c.rfile.read(10)
        c.wfile.write(b"foo")
        c.close()
        c.close()


class TestServerTimeOut(tservers.ServerTestBase):

    class handler(tcp.BaseHandler):

        def handle(self):
            self.timeout = False
            self.settimeout(0.01)
            try:
                self.rfile.read(10)
            except TcpTimeout:
                self.timeout = True

    def test_timeout(self):
        c = tcp.TCPClient(("127.0.0.1", self.port))
        c.connect()
        time.sleep(0.3)
        assert self.last_handler.timeout


class TestTimeOut(tservers.ServerTestBase):
    handler = HangHandler

    def test_timeout(self):
        c = tcp.TCPClient(("127.0.0.1", self.port))
        c.connect()
        c.settimeout(0.1)
        assert c.gettimeout() == 0.1
        tutils.raises(TcpTimeout, c.rfile.read, 10)


class TestALPNClient(tservers.ServerTestBase):
    handler = ALPNHandler
    ssl = dict(
        alpn_select=b"bar"
    )

    if tcp.HAS_ALPN:
        def test_alpn(self):
            c = tcp.TCPClient(("127.0.0.1", self.port))
            c.connect()
            c.convert_to_ssl(alpn_protos=[b"foo", b"bar", b"fasel"])
            assert c.get_alpn_proto_negotiated() == b"bar"
            assert c.rfile.readline().strip() == b"bar"

        def test_no_alpn(self):
            c = tcp.TCPClient(("127.0.0.1", self.port))
            c.connect()
            c.convert_to_ssl()
            assert c.get_alpn_proto_negotiated() == b""
            assert c.rfile.readline().strip() == b"NONE"

    else:
        def test_none_alpn(self):
            c = tcp.TCPClient(("127.0.0.1", self.port))
            c.connect()
            c.convert_to_ssl(alpn_protos=[b"foo", b"bar", b"fasel"])
            assert c.get_alpn_proto_negotiated() == b""
            assert c.rfile.readline() == b"NONE"


class TestNoSSLNoALPNClient(tservers.ServerTestBase):
    handler = ALPNHandler

    def test_no_ssl_no_alpn(self):
        c = tcp.TCPClient(("127.0.0.1", self.port))
        c.connect()
        assert c.get_alpn_proto_negotiated() == b""
        assert c.rfile.readline().strip() == b"NONE"


class TestSSLTimeOut(tservers.ServerTestBase):
    handler = HangHandler
    ssl = True

    def test_timeout_client(self):
        c = tcp.TCPClient(("127.0.0.1", self.port))
        c.connect()
        c.convert_to_ssl()
        c.settimeout(0.1)
        tutils.raises(TcpTimeout, c.rfile.read, 10)


class TestDHParams(tservers.ServerTestBase):
    handler = HangHandler
    ssl = dict(
        dhparams=certutils.CertStore.load_dhparam(
            tutils.test_data.path("data/dhparam.pem"),
        ),
        cipher_list="DHE-RSA-AES256-SHA"
    )

    def test_dhparams(self):
        c = tcp.TCPClient(("127.0.0.1", self.port))
        c.connect()
        c.convert_to_ssl()
        ret = c.get_current_cipher()
        assert ret[0] == "DHE-RSA-AES256-SHA"

    def test_create_dhparams(self):
        with tutils.tmpdir() as d:
            filename = os.path.join(d, "dhparam.pem")
            certutils.CertStore.load_dhparam(filename)
            assert os.path.exists(filename)


class TestTCPClient:

    def test_conerr(self):
        c = tcp.TCPClient(("127.0.0.1", 0))
        tutils.raises(TcpException, c.connect)


class TestFileLike:

    def test_blocksize(self):
        s = BytesIO(b"1234567890abcdefghijklmnopqrstuvwxyz")
        s = tcp.Reader(s)
        s.BLOCKSIZE = 2
        assert s.read(1) == b"1"
        assert s.read(2) == b"23"
        assert s.read(3) == b"456"
        assert s.read(4) == b"7890"
        d = s.read(-1)
        assert d.startswith(b"abc") and d.endswith(b"xyz")

    def test_wrap(self):
        s = BytesIO(b"foobar\nfoobar")
        s.flush()
        s = tcp.Reader(s)
        assert s.readline() == b"foobar\n"
        assert s.readline() == b"foobar"
        # Test __getattr__
        assert s.isatty

    def test_limit(self):
        s = BytesIO(b"foobar\nfoobar")
        s = tcp.Reader(s)
        assert s.readline(3) == b"foo"

    def test_limitless(self):
        s = BytesIO(b"f" * (50 * 1024))
        s = tcp.Reader(s)
        ret = s.read(-1)
        assert len(ret) == 50 * 1024

    def test_readlog(self):
        s = BytesIO(b"foobar\nfoobar")
        s = tcp.Reader(s)
        assert not s.is_logging()
        s.start_log()
        assert s.is_logging()
        s.readline()
        assert s.get_log() == b"foobar\n"
        s.read(1)
        assert s.get_log() == b"foobar\nf"
        s.start_log()
        assert s.get_log() == b""
        s.read(1)
        assert s.get_log() == b"o"
        s.stop_log()
        tutils.raises(ValueError, s.get_log)

    def test_writelog(self):
        s = BytesIO()
        s = tcp.Writer(s)
        s.start_log()
        assert s.is_logging()
        s.write(b"x")
        assert s.get_log() == b"x"
        s.write(b"x")
        assert s.get_log() == b"xx"

    def test_writer_flush_error(self):
        s = BytesIO()
        s = tcp.Writer(s)
        o = mock.MagicMock()
        o.flush = mock.MagicMock(side_effect=socket.error)
        s.o = o
        tutils.raises(TcpDisconnect, s.flush)

    def test_reader_read_error(self):
        s = BytesIO(b"foobar\nfoobar")
        s = tcp.Reader(s)
        o = mock.MagicMock()
        o.read = mock.MagicMock(side_effect=socket.error)
        s.o = o
        tutils.raises(TcpDisconnect, s.read, 10)

    def test_reset_timestamps(self):
        s = BytesIO(b"foobar\nfoobar")
        s = tcp.Reader(s)
        s.first_byte_timestamp = 500
        s.reset_timestamps()
        assert not s.first_byte_timestamp

    def test_first_byte_timestamp_updated_on_read(self):
        s = BytesIO(b"foobar\nfoobar")
        s = tcp.Reader(s)
        s.read(1)
        assert s.first_byte_timestamp
        expected = s.first_byte_timestamp
        s.read(5)
        assert s.first_byte_timestamp == expected

    def test_first_byte_timestamp_updated_on_readline(self):
        s = BytesIO(b"foobar\nfoobar\nfoobar")
        s = tcp.Reader(s)
        s.readline()
        assert s.first_byte_timestamp
        expected = s.first_byte_timestamp
        s.readline()
        assert s.first_byte_timestamp == expected

    def test_read_ssl_error(self):
        s = mock.MagicMock()
        s.read = mock.MagicMock(side_effect=SSL.Error())
        s = tcp.Reader(s)
        tutils.raises(TlsException, s.read, 1)

    def test_read_syscall_ssl_error(self):
        s = mock.MagicMock()
        s.read = mock.MagicMock(side_effect=SSL.SysCallError())
        s = tcp.Reader(s)
        tutils.raises(TlsException, s.read, 1)

    def test_reader_readline_disconnect(self):
        o = mock.MagicMock()
        o.read = mock.MagicMock(side_effect=socket.error)
        s = tcp.Reader(o)
        tutils.raises(TcpDisconnect, s.readline, 10)

    def test_reader_incomplete_error(self):
        s = BytesIO(b"foobar")
        s = tcp.Reader(s)
        tutils.raises(TcpReadIncomplete, s.safe_read, 10)


class TestPeek(tservers.ServerTestBase):
    handler = EchoHandler

    def _connect(self, c):
        c.connect()

    def test_peek(self):
        testval = b"peek!\n"
        c = tcp.TCPClient(("127.0.0.1", self.port))
        self._connect(c)
        c.wfile.write(testval)
        c.wfile.flush()

        assert c.rfile.peek(4) == b"peek"
        assert c.rfile.peek(6) == b"peek!\n"
        assert c.rfile.readline() == testval

        c.close()
        with tutils.raises(NetlibException):
            if c.rfile.peek(1) == b"":
                # Workaround for Python 2 on Unix:
                # Peeking a closed connection does not raise an exception here.
                raise NetlibException()


class TestPeekSSL(TestPeek):
    ssl = True

    def _connect(self, c):
        c.connect()
        c.convert_to_ssl()


class TestAddress:
    def test_simple(self):
        a = tcp.Address(("localhost", 80), True)
        assert a.use_ipv6
        b = tcp.Address(("foo.com", 80), True)
        assert not a == b
        c = tcp.Address(("localhost", 80), True)
        assert a == c
        assert not a != c
        assert repr(a) == "localhost:80"


class TestSSLKeyLogger(tservers.ServerTestBase):
    handler = EchoHandler
    ssl = dict(
        cipher_list="AES256-SHA"
    )

    def test_log(self):
        testval = b"echo!\n"
        _logfun = tcp.log_ssl_key

        with tutils.tmpdir() as d:
            logfile = os.path.join(d, "foo", "bar", "logfile")
            tcp.log_ssl_key = tcp.SSLKeyLogger(logfile)

            c = tcp.TCPClient(("127.0.0.1", self.port))
            c.connect()
            c.convert_to_ssl()
            c.wfile.write(testval)
            c.wfile.flush()
            assert c.rfile.readline() == testval
            c.finish()

            tcp.log_ssl_key.close()
            with open(logfile, "rb") as f:
                assert f.read().count(b"CLIENT_RANDOM") == 2

        tcp.log_ssl_key = _logfun

    def test_create_logfun(self):
        assert isinstance(
            tcp.SSLKeyLogger.create_logfun("test"),
            tcp.SSLKeyLogger)
        assert not tcp.SSLKeyLogger.create_logfun(False)
