from io import BytesIO
import re
import queue
import time
import socket
import random
import threading
import pytest
from unittest import mock
from OpenSSL import SSL

from mitmproxy import certs
from mitmproxy.net import tcp
from mitmproxy import exceptions
from mitmproxy.test import tutils
from ...conftest import skip_no_ipv6

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
        self.wfile.write(str(self.connection.get_cipher_list()).encode())
        self.wfile.flush()


class HangHandler(tcp.BaseHandler):

    def handle(self):
        # Hang as long as the client connection is alive
        while True:
            try:
                self.connection.setblocking(0)
                ret = self.connection.recv(1)
                # Client connection is dead...
                if ret == "" or ret == b"":
                    return
            except socket.error:
                pass
            except SSL.WantReadError:
                pass
            except Exception:
                return
            time.sleep(0.1)


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
        with c.connect():
            c.wfile.write(testval)
            c.wfile.flush()
            assert c.rfile.readline() == testval

    def test_thread_start_error(self):
        with mock.patch.object(threading.Thread, "start", side_effect=threading.ThreadError("nonewthread")) as m:
            c = tcp.TCPClient(("127.0.0.1", self.port))
            with c.connect():
                assert not c.rfile.read(1)
                assert m.called
                assert "nonewthread" in self.q.get_nowait()
        self.test_echo()


class TestServerBind(tservers.ServerTestBase):

    class handler(tcp.BaseHandler):

        def handle(self):
            # We may get an ipv4-mapped ipv6 address here, e.g. ::ffff:127.0.0.1.
            # Those still appear as "127.0.0.1" in the table, so we need to strip the prefix.
            peername = self.connection.getpeername()
            address = re.sub("^::ffff:(?=\d+.\d+.\d+.\d+$)", "", peername[0])
            port = peername[1]

            self.wfile.write(str((address, port)).encode())
            self.wfile.flush()

    def test_bind(self):
        """ Test to bind to a given random port. Try again if the random port turned out to be blocked. """
        for i in range(20):
            random_port = random.randrange(1024, 65535)
            try:
                c = tcp.TCPClient(
                    ("127.0.0.1", self.port), source_address=(
                        "127.0.0.1", random_port))
                with c.connect():
                    assert c.rfile.readline() == str(("127.0.0.1", random_port)).encode()
                    return
            except exceptions.TcpException:  # port probably already in use
                pass


@skip_no_ipv6
class TestServerIPv6(tservers.ServerTestBase):
    handler = EchoHandler
    addr = ("::1", 0)

    def test_echo(self):
        testval = b"echo!\n"
        c = tcp.TCPClient(("::1", self.port))
        with c.connect():
            c.wfile.write(testval)
            c.wfile.flush()
            assert c.rfile.readline() == testval


class TestEcho(tservers.ServerTestBase):
    handler = EchoHandler

    def test_echo(self):
        testval = b"echo!\n"
        c = tcp.TCPClient(("localhost", self.port))
        with c.connect():
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
        with c.connect():
            c.wfile.write(b"foo\n")
            c.wfile.flush = mock.Mock(side_effect=exceptions.TcpDisconnect)
            c.finish()


class TestServerSSL(tservers.ServerTestBase):
    handler = EchoHandler
    ssl = dict(
        cipher_list="AES256-SHA",
        chain_file=tutils.test_data.path("mitmproxy/net/data/server.crt")
    )

    def test_echo(self):
        c = tcp.TCPClient(("127.0.0.1", self.port))
        with c.connect():
            c.convert_to_tls(sni="foo.com", options=SSL.OP_ALL)
            testval = b"echo!\n"
            c.wfile.write(testval)
            c.wfile.flush()
            assert c.rfile.readline() == testval

    def test_get_current_cipher(self):
        c = tcp.TCPClient(("127.0.0.1", self.port))
        with c.connect():
            assert not c.get_current_cipher()
            c.convert_to_tls(sni="foo.com")
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
        with c.connect():
            with pytest.raises(exceptions.TlsException):
                c.convert_to_tls(sni="foo.com")


class TestInvalidTrustFile(tservers.ServerTestBase):
    def test_invalid_trust_file_should_fail(self):
        c = tcp.TCPClient(("127.0.0.1", self.port))
        with c.connect():
            with pytest.raises(exceptions.TlsException):
                c.convert_to_tls(
                    sni="example.mitmproxy.org",
                    verify=SSL.VERIFY_PEER,
                    ca_pemfile=tutils.test_data.path("mitmproxy/net/data/verificationcerts/generate.py")
                )


class TestSSLUpstreamCertVerificationWBadServerCert(tservers.ServerTestBase):
    handler = EchoHandler

    ssl = dict(
        cert=tutils.test_data.path("mitmproxy/net/data/verificationcerts/self-signed.crt"),
        key=tutils.test_data.path("mitmproxy/net/data/verificationcerts/self-signed.key")
    )

    def test_mode_default_should_pass(self):
        c = tcp.TCPClient(("127.0.0.1", self.port))
        with c.connect():
            c.convert_to_tls()

            # Verification errors should be saved even if connection isn't aborted
            # aborted
            assert c.ssl_verification_error

            testval = b"echo!\n"
            c.wfile.write(testval)
            c.wfile.flush()
            assert c.rfile.readline() == testval

    def test_mode_none_should_pass(self):
        c = tcp.TCPClient(("127.0.0.1", self.port))
        with c.connect():
            c.convert_to_tls(verify=SSL.VERIFY_NONE)

            # Verification errors should be saved even if connection isn't aborted
            assert c.ssl_verification_error

            testval = b"echo!\n"
            c.wfile.write(testval)
            c.wfile.flush()
            assert c.rfile.readline() == testval

    def test_mode_strict_should_fail(self):
        c = tcp.TCPClient(("127.0.0.1", self.port))
        with c.connect():
            with pytest.raises(exceptions.InvalidCertificateException):
                c.convert_to_tls(
                    sni="example.mitmproxy.org",
                    verify=SSL.VERIFY_PEER,
                    ca_pemfile=tutils.test_data.path("mitmproxy/net/data/verificationcerts/trusted-root.crt")
                )

            assert c.ssl_verification_error

            # Unknown issuing certificate authority for first certificate
            assert "errno: 18" in str(c.ssl_verification_error)
            assert "depth: 0" in str(c.ssl_verification_error)


class TestSSLUpstreamCertVerificationWBadHostname(tservers.ServerTestBase):
    handler = EchoHandler

    ssl = dict(
        cert=tutils.test_data.path("mitmproxy/net/data/verificationcerts/trusted-leaf.crt"),
        key=tutils.test_data.path("mitmproxy/net/data/verificationcerts/trusted-leaf.key")
    )

    def test_should_fail_without_sni(self):
        c = tcp.TCPClient(("127.0.0.1", self.port))
        with c.connect():
            with pytest.raises(exceptions.TlsException):
                c.convert_to_tls(
                    verify=SSL.VERIFY_PEER,
                    ca_pemfile=tutils.test_data.path("mitmproxy/net/data/verificationcerts/trusted-root.crt")
                )

    def test_mode_none_should_pass_without_sni(self):
        c = tcp.TCPClient(("127.0.0.1", self.port))
        with c.connect():
            c.convert_to_tls(
                verify=SSL.VERIFY_NONE,
                ca_path=tutils.test_data.path("mitmproxy/net/data/verificationcerts/")
            )

            assert "'no-hostname' doesn't match" in str(c.ssl_verification_error)

    def test_should_fail(self):
        c = tcp.TCPClient(("127.0.0.1", self.port))
        with c.connect():
            with pytest.raises(exceptions.InvalidCertificateException):
                c.convert_to_tls(
                    sni="mitmproxy.org",
                    verify=SSL.VERIFY_PEER,
                    ca_pemfile=tutils.test_data.path("mitmproxy/net/data/verificationcerts/trusted-root.crt")
                )
            assert c.ssl_verification_error


class TestSSLUpstreamCertVerificationWValidCertChain(tservers.ServerTestBase):
    handler = EchoHandler

    ssl = dict(
        cert=tutils.test_data.path("mitmproxy/net/data/verificationcerts/trusted-leaf.crt"),
        key=tutils.test_data.path("mitmproxy/net/data/verificationcerts/trusted-leaf.key")
    )

    def test_mode_strict_w_pemfile_should_pass(self):
        c = tcp.TCPClient(("127.0.0.1", self.port))
        with c.connect():
            c.convert_to_tls(
                sni="example.mitmproxy.org",
                verify=SSL.VERIFY_PEER,
                ca_pemfile=tutils.test_data.path("mitmproxy/net/data/verificationcerts/trusted-root.crt")
            )

            assert c.ssl_verification_error is None

            testval = b"echo!\n"
            c.wfile.write(testval)
            c.wfile.flush()
            assert c.rfile.readline() == testval

    def test_mode_strict_w_cadir_should_pass(self):
        c = tcp.TCPClient(("127.0.0.1", self.port))
        with c.connect():
            c.convert_to_tls(
                sni="example.mitmproxy.org",
                verify=SSL.VERIFY_PEER,
                ca_path=tutils.test_data.path("mitmproxy/net/data/verificationcerts/")
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
        with c.connect():
            c.convert_to_tls(
                cert=tutils.test_data.path("mitmproxy/net/data/clientcert/client.pem"))
            assert c.rfile.readline().strip() == b"1"

    def test_clientcert_err(self):
        c = tcp.TCPClient(("127.0.0.1", self.port))
        with c.connect():
            with pytest.raises(exceptions.TlsException):
                c.convert_to_tls(cert=tutils.test_data.path("mitmproxy/net/data/clientcert/make"))


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
        with c.connect():
            c.convert_to_tls(sni="foo.com")
            assert c.sni == "foo.com"
            assert c.rfile.readline() == b"foo.com"

    def test_idn(self):
        c = tcp.TCPClient(("127.0.0.1", self.port))
        with c.connect():
            c.convert_to_tls(sni="mitmproxyäöüß.example.com")
            assert c.tls_established
            assert "doesn't match" not in str(c.ssl_verification_error)


class TestServerCipherList(tservers.ServerTestBase):
    handler = ClientCipherListHandler
    ssl = dict(
        cipher_list='AES256-GCM-SHA384'
    )

    def test_echo(self):
        c = tcp.TCPClient(("127.0.0.1", self.port))
        with c.connect():
            c.convert_to_tls(sni="foo.com")
            expected = b"['AES256-GCM-SHA384']"
            assert c.rfile.read(len(expected) + 2) == expected


class TestServerCurrentCipher(tservers.ServerTestBase):

    class handler(tcp.BaseHandler):
        sni = None

        def handle(self):
            self.wfile.write(str(self.get_current_cipher()).encode())
            self.wfile.flush()

    ssl = dict(
        cipher_list='AES256-GCM-SHA384'
    )

    def test_echo(self):
        c = tcp.TCPClient(("127.0.0.1", self.port))
        with c.connect():
            c.convert_to_tls(sni="foo.com")
            assert b'AES256-GCM-SHA384' in c.rfile.readline()


class TestServerCipherListError(tservers.ServerTestBase):
    handler = ClientCipherListHandler
    ssl = dict(
        cipher_list=b'bogus'
    )

    def test_echo(self):
        c = tcp.TCPClient(("127.0.0.1", self.port))
        with c.connect():
            with pytest.raises(Exception, match="handshake error"):
                c.convert_to_tls(sni="foo.com")


class TestClientCipherListError(tservers.ServerTestBase):
    handler = ClientCipherListHandler
    ssl = dict(
        cipher_list='RC4-SHA'
    )

    def test_echo(self):
        c = tcp.TCPClient(("127.0.0.1", self.port))
        with c.connect():
            with pytest.raises(Exception, match="cipher specification"):
                c.convert_to_tls(sni="foo.com", cipher_list="bogus")


class TestSSLDisconnect(tservers.ServerTestBase):

    class handler(tcp.BaseHandler):

        def handle(self):
            self.finish()

    ssl = True

    def test_echo(self):
        c = tcp.TCPClient(("127.0.0.1", self.port))
        with c.connect():
            c.convert_to_tls()
            # Exercise SSL.ZeroReturnError
            c.rfile.read(10)
            c.close()
            with pytest.raises(exceptions.TcpDisconnect):
                c.wfile.write(b"foo")
            with pytest.raises(queue.Empty):
                self.q.get_nowait()


class TestSSLHardDisconnect(tservers.ServerTestBase):
    handler = HardDisconnectHandler
    ssl = True

    def test_echo(self):
        c = tcp.TCPClient(("127.0.0.1", self.port))
        with c.connect():
            c.convert_to_tls()
            # Exercise SSL.SysCallError
            c.rfile.read(10)
            c.close()
            with pytest.raises(exceptions.TcpDisconnect):
                c.wfile.write(b"foo")


class TestDisconnect(tservers.ServerTestBase):

    def test_echo(self):
        c = tcp.TCPClient(("127.0.0.1", self.port))
        with c.connect():
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
            except exceptions.TcpTimeout:
                self.timeout = True

    def test_timeout(self):
        c = tcp.TCPClient(("127.0.0.1", self.port))
        with c.connect():
            time.sleep(0.3)
            assert self.last_handler.timeout


class TestTimeOut(tservers.ServerTestBase):
    handler = HangHandler

    def test_timeout(self):
        c = tcp.TCPClient(("127.0.0.1", self.port))
        with c.connect():
            c.settimeout(0.1)
            assert c.gettimeout() == 0.1
            with pytest.raises(exceptions.TcpTimeout):
                c.rfile.read(10)


class TestALPNClient(tservers.ServerTestBase):
    handler = ALPNHandler
    ssl = dict(
        alpn_select=b"bar"
    )

    @pytest.mark.parametrize('alpn_protos, expected_negotiated, expected_response', [
        ([b"foo", b"bar", b"fasel"], b'bar', b'bar'),
        ([], b'', b'NONE'),
        (None, b'', b'NONE'),
    ])
    def test_alpn(self, monkeypatch, alpn_protos, expected_negotiated, expected_response):
        c = tcp.TCPClient(("127.0.0.1", self.port))
        with c.connect():
            c.convert_to_tls(alpn_protos=alpn_protos)
            assert c.get_alpn_proto_negotiated() == expected_negotiated
            assert c.rfile.readline().strip() == expected_response


class TestNoSSLNoALPNClient(tservers.ServerTestBase):
    handler = ALPNHandler

    def test_no_ssl_no_alpn(self):
        c = tcp.TCPClient(("127.0.0.1", self.port))
        with c.connect():
            assert c.get_alpn_proto_negotiated() == b""
            assert c.rfile.readline().strip() == b"NONE"


class TestSSLTimeOut(tservers.ServerTestBase):
    handler = HangHandler
    ssl = True

    def test_timeout_client(self):
        c = tcp.TCPClient(("127.0.0.1", self.port))
        with c.connect():
            c.convert_to_tls()
            c.settimeout(0.1)
            with pytest.raises(exceptions.TcpTimeout):
                c.rfile.read(10)


class TestDHParams(tservers.ServerTestBase):
    handler = HangHandler
    ssl = dict(
        dhparams=certs.CertStore.load_dhparam(
            tutils.test_data.path("mitmproxy/net/data/dhparam.pem"),
        ),
        cipher_list="DHE-RSA-AES256-SHA"
    )

    def test_dhparams(self):
        c = tcp.TCPClient(("127.0.0.1", self.port))
        with c.connect():
            c.convert_to_tls()
            ret = c.get_current_cipher()
            assert ret[0] == "DHE-RSA-AES256-SHA"


class TestTCPClient(tservers.ServerTestBase):

    def test_conerr(self):
        c = tcp.TCPClient(("127.0.0.1", 0))
        with pytest.raises(exceptions.TcpException, match="Error connecting"):
            c.connect()

    def test_timeout(self):
        c = tcp.TCPClient(("127.0.0.1", self.port))
        with c.create_connection(timeout=20) as conn:
            assert conn.gettimeout() == 20

    def test_spoof_address(self):
        c = tcp.TCPClient(("127.0.0.1", self.port), spoof_source_address=("127.0.0.1", 0))
        with pytest.raises(exceptions.TcpException, match="Failed to spoof"):
            c.connect()


class TestTCPServer:

    def test_binderr(self):
        with pytest.raises(socket.error, match="prohibited"):
            tcp.TCPServer(("localhost", 8080))

    def test_wait_for_silence(self):
        s = tcp.TCPServer(("127.0.0.1", 0))
        with s.handler_counter:
            with pytest.raises(exceptions.Timeout):
                s.wait_for_silence()
            s.shutdown()


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
        with pytest.raises(ValueError):
            s.get_log()

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
        with pytest.raises(exceptions.TcpDisconnect):
            s.flush()

    def test_reader_read_error(self):
        s = BytesIO(b"foobar\nfoobar")
        s = tcp.Reader(s)
        o = mock.MagicMock()
        o.read = mock.MagicMock(side_effect=socket.error)
        s.o = o
        with pytest.raises(exceptions.TcpDisconnect):
            s.read(10)

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
        with pytest.raises(exceptions.TlsException):
            s.read(1)

    def test_read_syscall_ssl_error(self):
        s = mock.MagicMock()
        s.read = mock.MagicMock(side_effect=SSL.SysCallError())
        s = tcp.Reader(s)
        with pytest.raises(exceptions.TlsException):
            s.read(1)

    def test_reader_readline_disconnect(self):
        o = mock.MagicMock()
        o.read = mock.MagicMock(side_effect=socket.error)
        s = tcp.Reader(o)
        with pytest.raises(exceptions.TcpDisconnect):
            s.readline(10)

    def test_reader_incomplete_error(self):
        s = BytesIO(b"foobar")
        s = tcp.Reader(s)
        with pytest.raises(exceptions.TcpReadIncomplete):
            s.safe_read(10)


class TestPeek(tservers.ServerTestBase):
    handler = EchoHandler

    def _connect(self, c):
        return c.connect()

    def test_peek(self):
        testval = b"peek!\n"
        c = tcp.TCPClient(("127.0.0.1", self.port))
        with self._connect(c):
            c.wfile.write(testval)
            c.wfile.flush()

            assert c.rfile.peek(4) == b"peek"
            assert c.rfile.peek(6) == b"peek!\n"
            assert c.rfile.readline() == testval

            c.close()
            with pytest.raises(exceptions.NetlibException):
                c.rfile.peek(1)


class TestPeekSSL(TestPeek):
    ssl = True

    def _connect(self, c):
        with c.connect() as conn:
            c.convert_to_tls()
            return conn.pop()
