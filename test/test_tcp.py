import cStringIO, Queue, time, socket, random
from netlib import tcp, certutils, test
import mock
import tutils

class SNIHandler(tcp.BaseHandler):
    sni = None
    def handle_sni(self, connection):
        self.sni = connection.get_servername()

    def handle(self):
        self.wfile.write(self.sni)
        self.wfile.flush()


class EchoHandler(tcp.BaseHandler):
    sni = None
    def handle_sni(self, connection):
        self.sni = connection.get_servername()

    def handle(self):
        v = self.rfile.readline()
        self.wfile.write(v)
        self.wfile.flush()


class ClientPeernameHandler(tcp.BaseHandler):
    def handle(self):
        self.wfile.write(str(self.connection.getpeername()))
        self.wfile.flush()


class CertHandler(tcp.BaseHandler):
    sni = None
    def handle_sni(self, connection):
        self.sni = connection.get_servername()

    def handle(self):
        self.wfile.write("%s\n"%self.clientcert.serial)
        self.wfile.flush()


class ClientCipherListHandler(tcp.BaseHandler):
    sni = None

    def handle(self):
        self.wfile.write("%s"%self.connection.get_cipher_list())
        self.wfile.flush()


class DisconnectHandler(tcp.BaseHandler):
    def handle(self):
        self.close()


class HangHandler(tcp.BaseHandler):
    def handle(self):
        while 1:
            time.sleep(1)


class TimeoutHandler(tcp.BaseHandler):
    def handle(self):
        self.timeout = False
        self.settimeout(0.01)
        try:
            self.rfile.read(10)
        except tcp.NetLibTimeout:
            self.timeout = True


class TestServer(test.ServerTestBase):
    handler = EchoHandler
    def test_echo(self):
        testval = "echo!\n"
        c = tcp.TCPClient("127.0.0.1", self.port)
        c.connect()
        c.wfile.write(testval)
        c.wfile.flush()
        assert c.rfile.readline() == testval


class TestServerBind(test.ServerTestBase):
    handler = ClientPeernameHandler

    def test_bind(self):
        """ Test to bind to a given random port. Try again if the random port turned out to be blocked. """
        for i in range(20):
            random_port = random.randrange(1024, 65535)
            try:
                c = tcp.TCPClient("127.0.0.1", self.port, source_address=("127.0.0.1", random_port))
                c.connect()
                assert c.rfile.readline() == str(("127.0.0.1", random_port))
                return
            except tcp.NetLibError: # port probably already in use
                pass


class TestServerIPv6(test.ServerTestBase):
    handler = EchoHandler
    use_ipv6 = True

    def test_echo(self):
        testval = "echo!\n"
        c = tcp.TCPClient("::1", self.port, use_ipv6=True)
        c.connect()
        c.wfile.write(testval)
        c.wfile.flush()
        assert c.rfile.readline() == testval


class FinishFailHandler(tcp.BaseHandler):
    def handle(self):
        v = self.rfile.readline()
        self.wfile.write(v)
        self.wfile.flush()
        self.wfile.close()
        self.rfile.close()
        self.close = mock.MagicMock(side_effect=socket.error)


class TestFinishFail(test.ServerTestBase):
    """
        This tests a difficult-to-trigger exception in the .finish() method of
        the handler.
    """
    handler = FinishFailHandler
    def test_disconnect_in_finish(self):
        testval = "echo!\n"
        c = tcp.TCPClient("127.0.0.1", self.port)
        c.connect()
        c.wfile.write("foo\n")
        c.wfile.flush()
        c.rfile.read(4)

class TestDisconnect(test.ServerTestBase):
    handler = EchoHandler
    def test_echo(self):
        testval = "echo!\n"
        c = tcp.TCPClient("127.0.0.1", self.port)
        c.connect()
        c.wfile.write(testval)
        c.wfile.flush()
        assert c.rfile.readline() == testval


class TestServerSSL(test.ServerTestBase):
    handler = EchoHandler
    ssl = dict(
                cert = tutils.test_data.path("data/server.crt"),
                key = tutils.test_data.path("data/server.key"),
                request_client_cert = False,
                v3_only = False
            )
    def test_echo(self):
        c = tcp.TCPClient("127.0.0.1", self.port)
        c.connect()
        c.convert_to_ssl(sni="foo.com", options=tcp.OP_ALL)
        testval = "echo!\n"
        c.wfile.write(testval)
        c.wfile.flush()
        assert c.rfile.readline() == testval

    def test_get_remote_cert(self):
        assert certutils.get_remote_cert("127.0.0.1", self.port, None).digest("sha1")


class TestSSLv3Only(test.ServerTestBase):
    handler = EchoHandler
    ssl = dict(
        cert = tutils.test_data.path("data/server.crt"),
        key = tutils.test_data.path("data/server.key"),
        request_client_cert = False,
        v3_only = True
    )
    def test_failure(self):
        c = tcp.TCPClient("127.0.0.1", self.port)
        c.connect()
        tutils.raises(tcp.NetLibError, c.convert_to_ssl, sni="foo.com", method=tcp.TLSv1_METHOD)


class TestSSLClientCert(test.ServerTestBase):
    handler = CertHandler
    ssl = dict(
        cert = tutils.test_data.path("data/server.crt"),
        key = tutils.test_data.path("data/server.key"),
        request_client_cert = True,
        v3_only = False
    )
    def test_clientcert(self):
        c = tcp.TCPClient("127.0.0.1", self.port)
        c.connect()
        c.convert_to_ssl(cert=tutils.test_data.path("data/clientcert/client.pem"))
        assert c.rfile.readline().strip() == "1"

    def test_clientcert_err(self):
        c = tcp.TCPClient("127.0.0.1", self.port)
        c.connect()
        tutils.raises(
            tcp.NetLibError,
            c.convert_to_ssl,
            cert=tutils.test_data.path("data/clientcert/make")
        )


class TestSNI(test.ServerTestBase):
    handler = SNIHandler
    ssl = dict(
        cert = tutils.test_data.path("data/server.crt"),
        key = tutils.test_data.path("data/server.key"),
        request_client_cert = False,
        v3_only = False
    )
    def test_echo(self):
        c = tcp.TCPClient("127.0.0.1", self.port)
        c.connect()
        c.convert_to_ssl(sni="foo.com")
        assert c.rfile.readline() == "foo.com"


class TestClientCipherList(test.ServerTestBase):
    handler = ClientCipherListHandler
    ssl = dict(
        cert = tutils.test_data.path("data/server.crt"),
        key = tutils.test_data.path("data/server.key"),
        request_client_cert = False,
        v3_only = False,
        cipher_list = 'RC4-SHA'
    )
    def test_echo(self):
        c = tcp.TCPClient("127.0.0.1", self.port)
        c.connect()
        c.convert_to_ssl(sni="foo.com")
        assert c.rfile.readline() == "['RC4-SHA']"


class TestSSLDisconnect(test.ServerTestBase):
    handler = DisconnectHandler
    ssl = dict(
        cert = tutils.test_data.path("data/server.crt"),
        key = tutils.test_data.path("data/server.key"),
        request_client_cert = False,
        v3_only = False
    )
    def test_echo(self):
        c = tcp.TCPClient("127.0.0.1", self.port)
        c.connect()
        c.convert_to_ssl()
        # Excercise SSL.ZeroReturnError
        c.rfile.read(10)
        c.close()
        tutils.raises(tcp.NetLibDisconnect, c.wfile.write, "foo")
        tutils.raises(Queue.Empty, self.q.get_nowait)


class TestDisconnect(test.ServerTestBase):
    def test_echo(self):
        c = tcp.TCPClient("127.0.0.1", self.port)
        c.connect()
        c.rfile.read(10)
        c.wfile.write("foo")
        c.close()
        c.close()


class TestServerTimeOut(test.ServerTestBase):
    handler = TimeoutHandler
    def test_timeout(self):
        c = tcp.TCPClient("127.0.0.1", self.port)
        c.connect()
        time.sleep(0.3)
        assert self.last_handler.timeout


class TestTimeOut(test.ServerTestBase):
    handler = HangHandler
    def test_timeout(self):
        c = tcp.TCPClient("127.0.0.1", self.port)
        c.connect()
        c.settimeout(0.1)
        assert c.gettimeout() == 0.1
        tutils.raises(tcp.NetLibTimeout, c.rfile.read, 10)


class TestSSLTimeOut(test.ServerTestBase):
    handler = HangHandler
    ssl = dict(
        cert = tutils.test_data.path("data/server.crt"),
        key = tutils.test_data.path("data/server.key"),
        request_client_cert = False,
        v3_only = False
    )
    def test_timeout_client(self):
        c = tcp.TCPClient("127.0.0.1", self.port)
        c.connect()
        c.convert_to_ssl()
        c.settimeout(0.1)
        tutils.raises(tcp.NetLibTimeout, c.rfile.read, 10)


class TestTCPClient:
    def test_conerr(self):
        c = tcp.TCPClient("127.0.0.1", 0)
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
        s = cStringIO.StringIO("f"*(50*1024))
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

