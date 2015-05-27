import cStringIO
import Queue
import time
import socket
import random
import os
from netlib import tcp, certutils, test, certffi
import threading
import mock
import tutils
from OpenSSL import SSL


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


class TestServer(test.ServerTestBase):
    handler = EchoHandler

    def test_echo(self):
        testval = "echo!\n"
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


class TestServerBind(test.ServerTestBase):

    class handler(tcp.BaseHandler):

        def handle(self):
            self.wfile.write(str(self.connection.getpeername()))
            self.wfile.flush()

    def test_bind(self):
        """ Test to bind to a given random port. Try again if the random port turned out to be blocked. """
        for i in range(20):
            random_port = random.randrange(1024, 65535)
            try:
                c = tcp.TCPClient(("127.0.0.1", self.port), source_address=("127.0.0.1", random_port))
                c.connect()
                assert c.rfile.readline() == str(("127.0.0.1", random_port))
                return
            except tcp.NetLibError:  # port probably already in use
                pass


class TestServerIPv6(test.ServerTestBase):
    handler = EchoHandler
    addr = tcp.Address(("localhost", 0), use_ipv6=True)

    def test_echo(self):
        testval = "echo!\n"
        c = tcp.TCPClient(tcp.Address(("::1", self.port), use_ipv6=True))
        c.connect()
        c.wfile.write(testval)
        c.wfile.flush()
        assert c.rfile.readline() == testval


class TestEcho(test.ServerTestBase):
    handler = EchoHandler

    def test_echo(self):
        testval = "echo!\n"
        c = tcp.TCPClient(("127.0.0.1", self.port))
        c.connect()
        c.wfile.write(testval)
        c.wfile.flush()
        assert c.rfile.readline() == testval


class HardDisconnectHandler(tcp.BaseHandler):

    def handle(self):
        self.connection.close()


class TestFinishFail(test.ServerTestBase):

    """
        This tests a difficult-to-trigger exception in the .finish() method of
        the handler.
    """
    handler = EchoHandler

    def test_disconnect_in_finish(self):
        c = tcp.TCPClient(("127.0.0.1", self.port))
        c.connect()
        c.wfile.write("foo\n")
        c.wfile.flush = mock.Mock(side_effect=tcp.NetLibDisconnect)
        c.finish()


class TestServerSSL(test.ServerTestBase):
    handler = EchoHandler
    ssl = dict(
        cert=tutils.test_data.path("data/server.crt"),
        key=tutils.test_data.path("data/server.key"),
        request_client_cert=False,
        v3_only=False,
        cipher_list="AES256-SHA",
        chain_file=tutils.test_data.path("data/server.crt")
    )

    def test_echo(self):
        c = tcp.TCPClient(("127.0.0.1", self.port))
        c.connect()
        c.convert_to_ssl(sni="foo.com", options=SSL.OP_ALL)
        testval = "echo!\n"
        c.wfile.write(testval)
        c.wfile.flush()
        assert c.rfile.readline() == testval

    def test_get_current_cipher(self):
        c = tcp.TCPClient(("127.0.0.1", self.port))
        c.connect()
        assert not c.get_current_cipher()
        c.convert_to_ssl(sni="foo.com")
        ret = c.get_current_cipher()
        assert ret
        assert "AES" in ret[0]


class TestSSLv3Only(test.ServerTestBase):
    handler = EchoHandler
    ssl = dict(
        cert=tutils.test_data.path("data/server.crt"),
        key=tutils.test_data.path("data/server.key"),
        request_client_cert=False,
        v3_only=True
    )

    def test_failure(self):
        c = tcp.TCPClient(("127.0.0.1", self.port))
        c.connect()
        tutils.raises(tcp.NetLibError, c.convert_to_ssl, sni="foo.com")


class TestSSLClientCert(test.ServerTestBase):

    class handler(tcp.BaseHandler):
        sni = None

        def handle_sni(self, connection):
            self.sni = connection.get_servername()

        def handle(self):
            self.wfile.write("%s\n" % self.clientcert.serial)
            self.wfile.flush()
    ssl = dict(
        cert=tutils.test_data.path("data/server.crt"),
        key=tutils.test_data.path("data/server.key"),
        request_client_cert=True,
        v3_only=False
    )

    def test_clientcert(self):
        c = tcp.TCPClient(("127.0.0.1", self.port))
        c.connect()
        c.convert_to_ssl(cert=tutils.test_data.path("data/clientcert/client.pem"))
        assert c.rfile.readline().strip() == "1"

    def test_clientcert_err(self):
        c = tcp.TCPClient(("127.0.0.1", self.port))
        c.connect()
        tutils.raises(
            tcp.NetLibError,
            c.convert_to_ssl,
            cert=tutils.test_data.path("data/clientcert/make")
        )


class TestSNI(test.ServerTestBase):

    class handler(tcp.BaseHandler):
        sni = None

        def handle_sni(self, connection):
            self.sni = connection.get_servername()

        def handle(self):
            self.wfile.write(self.sni)
            self.wfile.flush()

    ssl = dict(
        cert=tutils.test_data.path("data/server.crt"),
        key=tutils.test_data.path("data/server.key"),
        request_client_cert=False,
        v3_only=False
    )

    def test_echo(self):
        c = tcp.TCPClient(("127.0.0.1", self.port))
        c.connect()
        c.convert_to_ssl(sni="foo.com")
        assert c.sni == "foo.com"
        assert c.rfile.readline() == "foo.com"


class TestServerCipherList(test.ServerTestBase):
    handler = ClientCipherListHandler
    ssl = dict(
        cert=tutils.test_data.path("data/server.crt"),
        key=tutils.test_data.path("data/server.key"),
        request_client_cert=False,
        v3_only=False,
        cipher_list='RC4-SHA'
    )

    def test_echo(self):
        c = tcp.TCPClient(("127.0.0.1", self.port))
        c.connect()
        c.convert_to_ssl(sni="foo.com")
        assert c.rfile.readline() == "['RC4-SHA']"


class TestServerCurrentCipher(test.ServerTestBase):

    class handler(tcp.BaseHandler):
        sni = None

        def handle(self):
            self.wfile.write("%s" % str(self.get_current_cipher()))
            self.wfile.flush()
    ssl = dict(
        cert=tutils.test_data.path("data/server.crt"),
        key=tutils.test_data.path("data/server.key"),
        request_client_cert=False,
        v3_only=False,
        cipher_list='RC4-SHA'
    )

    def test_echo(self):
        c = tcp.TCPClient(("127.0.0.1", self.port))
        c.connect()
        c.convert_to_ssl(sni="foo.com")
        assert "RC4-SHA" in c.rfile.readline()


class TestServerCipherListError(test.ServerTestBase):
    handler = ClientCipherListHandler
    ssl = dict(
        cert=tutils.test_data.path("data/server.crt"),
        key=tutils.test_data.path("data/server.key"),
        request_client_cert=False,
        v3_only=False,
        cipher_list='bogus'
    )

    def test_echo(self):
        c = tcp.TCPClient(("127.0.0.1", self.port))
        c.connect()
        tutils.raises("handshake error", c.convert_to_ssl, sni="foo.com")


class TestClientCipherListError(test.ServerTestBase):
    handler = ClientCipherListHandler
    ssl = dict(
        cert=tutils.test_data.path("data/server.crt"),
        key=tutils.test_data.path("data/server.key"),
        request_client_cert=False,
        v3_only=False,
        cipher_list='RC4-SHA'
    )

    def test_echo(self):
        c = tcp.TCPClient(("127.0.0.1", self.port))
        c.connect()
        tutils.raises("cipher specification", c.convert_to_ssl, sni="foo.com", cipher_list="bogus")


class TestSSLDisconnect(test.ServerTestBase):

    class handler(tcp.BaseHandler):

        def handle(self):
            self.finish()
    ssl = dict(
        cert=tutils.test_data.path("data/server.crt"),
        key=tutils.test_data.path("data/server.key"),
        request_client_cert=False,
        v3_only=False
    )

    def test_echo(self):
        c = tcp.TCPClient(("127.0.0.1", self.port))
        c.connect()
        c.convert_to_ssl()
        # Excercise SSL.ZeroReturnError
        c.rfile.read(10)
        c.close()
        tutils.raises(tcp.NetLibDisconnect, c.wfile.write, "foo")
        tutils.raises(Queue.Empty, self.q.get_nowait)


class TestSSLHardDisconnect(test.ServerTestBase):
    handler = HardDisconnectHandler
    ssl = dict(
        cert=tutils.test_data.path("data/server.crt"),
        key=tutils.test_data.path("data/server.key"),
        request_client_cert=False,
        v3_only=False
    )

    def test_echo(self):
        c = tcp.TCPClient(("127.0.0.1", self.port))
        c.connect()
        c.convert_to_ssl()
        # Exercise SSL.SysCallError
        c.rfile.read(10)
        c.close()
        tutils.raises(tcp.NetLibDisconnect, c.wfile.write, "foo")


class TestDisconnect(test.ServerTestBase):

    def test_echo(self):
        c = tcp.TCPClient(("127.0.0.1", self.port))
        c.connect()
        c.rfile.read(10)
        c.wfile.write("foo")
        c.close()
        c.close()


class TestServerTimeOut(test.ServerTestBase):

    class handler(tcp.BaseHandler):

        def handle(self):
            self.timeout = False
            self.settimeout(0.01)
            try:
                self.rfile.read(10)
            except tcp.NetLibTimeout:
                self.timeout = True

    def test_timeout(self):
        c = tcp.TCPClient(("127.0.0.1", self.port))
        c.connect()
        time.sleep(0.3)
        assert self.last_handler.timeout


class TestTimeOut(test.ServerTestBase):
    handler = HangHandler

    def test_timeout(self):
        c = tcp.TCPClient(("127.0.0.1", self.port))
        c.connect()
        c.settimeout(0.1)
        assert c.gettimeout() == 0.1
        tutils.raises(tcp.NetLibTimeout, c.rfile.read, 10)


class TestSSLTimeOut(test.ServerTestBase):
    handler = HangHandler
    ssl = dict(
        cert=tutils.test_data.path("data/server.crt"),
        key=tutils.test_data.path("data/server.key"),
        request_client_cert=False,
        v3_only=False
    )

    def test_timeout_client(self):
        c = tcp.TCPClient(("127.0.0.1", self.port))
        c.connect()
        c.convert_to_ssl()
        c.settimeout(0.1)
        tutils.raises(tcp.NetLibTimeout, c.rfile.read, 10)


class TestDHParams(test.ServerTestBase):
    handler = HangHandler
    ssl = dict(
        cert=tutils.test_data.path("data/server.crt"),
        key=tutils.test_data.path("data/server.key"),
        request_client_cert=False,
        v3_only=False,
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


class TestPrivkeyGen(test.ServerTestBase):

    class handler(tcp.BaseHandler):

        def handle(self):
            with tutils.tmpdir() as d:
                ca1 = certutils.CertStore.from_store(d, "test2")
                ca2 = certutils.CertStore.from_store(d, "test3")
                cert, _, _ = ca1.get_cert("foo.com", [])
                key = ca2.gen_pkey(cert)
                self.convert_to_ssl(cert, key)

    def test_privkey(self):
        c = tcp.TCPClient(("127.0.0.1", self.port))
        c.connect()
        tutils.raises("bad record mac", c.convert_to_ssl)


class TestPrivkeyGenNoFlags(test.ServerTestBase):

    class handler(tcp.BaseHandler):

        def handle(self):
            with tutils.tmpdir() as d:
                ca1 = certutils.CertStore.from_store(d, "test2")
                ca2 = certutils.CertStore.from_store(d, "test3")
                cert, _, _ = ca1.get_cert("foo.com", [])
                certffi.set_flags(ca2.default_privatekey, 0)
                self.convert_to_ssl(cert, ca2.default_privatekey)

    def test_privkey(self):
        c = tcp.TCPClient(("127.0.0.1", self.port))
        c.connect()
        tutils.raises("sslv3 alert handshake failure", c.convert_to_ssl)


class TestTCPClient:

    def test_conerr(self):
        c = tcp.TCPClient(("127.0.0.1", 0))
        tutils.raises(tcp.NetLibError, c.connect)


class TestFileLike:

    def test_blocksize(self):
        s = cStringIO.StringIO("1234567890abcdefghijklmnopqrstuvwxyz")
        s = tcp.Reader(s)
        s.BLOCKSIZE = 2
        assert s.read(1) == "1"
        assert s.read(2) == "23"
        assert s.read(3) == "456"
        assert s.read(4) == "7890"
        d = s.read(-1)
        assert d.startswith("abc") and d.endswith("xyz")

    def test_wrap(self):
        s = cStringIO.StringIO("foobar\nfoobar")
        s.flush()
        s = tcp.Reader(s)
        assert s.readline() == "foobar\n"
        assert s.readline() == "foobar"
        # Test __getattr__
        assert s.isatty

    def test_limit(self):
        s = cStringIO.StringIO("foobar\nfoobar")
        s = tcp.Reader(s)
        assert s.readline(3) == "foo"

    def test_limitless(self):
        s = cStringIO.StringIO("f" * (50 * 1024))
        s = tcp.Reader(s)
        ret = s.read(-1)
        assert len(ret) == 50 * 1024

    def test_readlog(self):
        s = cStringIO.StringIO("foobar\nfoobar")
        s = tcp.Reader(s)
        assert not s.is_logging()
        s.start_log()
        assert s.is_logging()
        s.readline()
        assert s.get_log() == "foobar\n"
        s.read(1)
        assert s.get_log() == "foobar\nf"
        s.start_log()
        assert s.get_log() == ""
        s.read(1)
        assert s.get_log() == "o"
        s.stop_log()
        tutils.raises(ValueError, s.get_log)

    def test_writelog(self):
        s = cStringIO.StringIO()
        s = tcp.Writer(s)
        s.start_log()
        assert s.is_logging()
        s.write("x")
        assert s.get_log() == "x"
        s.write("x")
        assert s.get_log() == "xx"

    def test_writer_flush_error(self):
        s = cStringIO.StringIO()
        s = tcp.Writer(s)
        o = mock.MagicMock()
        o.flush = mock.MagicMock(side_effect=socket.error)
        s.o = o
        tutils.raises(tcp.NetLibDisconnect, s.flush)

    def test_reader_read_error(self):
        s = cStringIO.StringIO("foobar\nfoobar")
        s = tcp.Reader(s)
        o = mock.MagicMock()
        o.read = mock.MagicMock(side_effect=socket.error)
        s.o = o
        tutils.raises(tcp.NetLibDisconnect, s.read, 10)

    def test_reset_timestamps(self):
        s = cStringIO.StringIO("foobar\nfoobar")
        s = tcp.Reader(s)
        s.first_byte_timestamp = 500
        s.reset_timestamps()
        assert not s.first_byte_timestamp

    def test_first_byte_timestamp_updated_on_read(self):
        s = cStringIO.StringIO("foobar\nfoobar")
        s = tcp.Reader(s)
        s.read(1)
        assert s.first_byte_timestamp
        expected = s.first_byte_timestamp
        s.read(5)
        assert s.first_byte_timestamp == expected

    def test_first_byte_timestamp_updated_on_readline(self):
        s = cStringIO.StringIO("foobar\nfoobar\nfoobar")
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
        tutils.raises(tcp.NetLibSSLError, s.read, 1)

    def test_read_syscall_ssl_error(self):
        s = mock.MagicMock()
        s.read = mock.MagicMock(side_effect=SSL.SysCallError())
        s = tcp.Reader(s)
        tutils.raises(tcp.NetLibSSLError, s.read, 1)

    def test_reader_readline_disconnect(self):
        o = mock.MagicMock()
        o.read = mock.MagicMock(side_effect=socket.error)
        s = tcp.Reader(o)
        tutils.raises(tcp.NetLibDisconnect, s.readline, 10)


class TestAddress:

    def test_simple(self):
        a = tcp.Address("localhost", True)
        assert a.use_ipv6
        b = tcp.Address("foo.com", True)
        assert not a == b
        c = tcp.Address("localhost", True)
        assert a == c
        assert not a != c
        assert repr(a)


class TestSSLKeyLogger(test.ServerTestBase):
    handler = EchoHandler
    ssl = dict(
        cert=tutils.test_data.path("data/server.crt"),
        key=tutils.test_data.path("data/server.key"),
        request_client_cert=False,
        v3_only=False,
        cipher_list="AES256-SHA"
    )

    def test_log(self):
        testval = "echo!\n"
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
                assert f.read().count("CLIENT_RANDOM") == 2

        tcp.log_ssl_key = _logfun

    def test_create_logfun(self):
        assert isinstance(tcp.SSLKeyLogger.create_logfun("test"), tcp.SSLKeyLogger)
        assert not tcp.SSLKeyLogger.create_logfun(False)
