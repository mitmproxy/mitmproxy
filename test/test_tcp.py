import cStringIO, threading, Queue, time
from netlib import tcp, certutils
import tutils

class ServerThread(threading.Thread):
    def __init__(self, server):
        self.server = server
        threading.Thread.__init__(self)

    def run(self):
        self.server.serve_forever()

    def shutdown(self):
        self.server.shutdown()


class ServerTestBase:
    @classmethod
    def setupAll(cls):
        cls.q = Queue.Queue()
        s = cls.makeserver()
        cls.port = s.port
        cls.server = ServerThread(s)
        cls.server.start()

    @classmethod
    def teardownAll(cls):
        cls.server.shutdown()


    @property
    def last_handler(self):
        return self.server.server.last_handler


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
        if v.startswith("echo"):
            self.wfile.write(v)
        elif v.startswith("error"):
            raise ValueError("Testing an error.")
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


class TServer(tcp.TCPServer):
    def __init__(self, addr, ssl, q, handler_klass, v3_only=False):
        tcp.TCPServer.__init__(self, addr)
        self.ssl, self.q = ssl, q
        self.v3_only = v3_only
        self.handler_klass = handler_klass
        self.last_handler = None

    def handle_connection(self, request, client_address):
        h = self.handler_klass(request, client_address, self)
        self.last_handler = h
        if self.ssl:
            if self.v3_only:
                method = tcp.SSLv3_METHOD
                options = tcp.OP_NO_SSLv2|tcp.OP_NO_TLSv1
            else:
                method = tcp.SSLv23_METHOD
                options = None
            h.convert_to_ssl(
                tutils.test_data.path("data/server.crt"),
                tutils.test_data.path("data/server.key"),
                method = method,
                options = options,
            )
        h.handle()
        h.finish()

    def handle_error(self, request, client_address):
        s = cStringIO.StringIO()
        tcp.TCPServer.handle_error(self, request, client_address, s)
        self.q.put(s.getvalue())


class TestServer(ServerTestBase):
    @classmethod
    def makeserver(cls):
        return TServer(("127.0.0.1", 0), False, cls.q, EchoHandler)

    def test_echo(self):
        testval = "echo!\n"
        c = tcp.TCPClient("127.0.0.1", self.port)
        c.connect()
        c.wfile.write(testval)
        c.wfile.flush()
        assert c.rfile.readline() == testval


class TestDisconnect(ServerTestBase):
    @classmethod
    def makeserver(cls):
        return TServer(("127.0.0.1", 0), False, cls.q, EchoHandler)

    def test_echo(self):
        testval = "echo!\n"
        c = tcp.TCPClient("127.0.0.1", self.port)
        c.connect()
        c.wfile.write(testval)
        c.wfile.flush()
        assert c.rfile.readline() == testval


class TestServerSSL(ServerTestBase):
    @classmethod
    def makeserver(cls):
        return TServer(("127.0.0.1", 0), True, cls.q, EchoHandler)

    def test_echo(self):
        c = tcp.TCPClient("127.0.0.1", self.port)
        c.connect()
        c.convert_to_ssl(sni="foo.com")
        testval = "echo!\n"
        c.wfile.write(testval)
        c.wfile.flush()
        assert c.rfile.readline() == testval

    def test_get_remote_cert(self):
        assert certutils.get_remote_cert("127.0.0.1", self.port, None).digest("sha1")


class TestSSLv3Only(ServerTestBase):
    @classmethod
    def makeserver(cls):
        return TServer(("127.0.0.1", 0), True, cls.q, EchoHandler, True)

    def test_failure(self):
        c = tcp.TCPClient("127.0.0.1", self.port)
        c.connect()
        tutils.raises(tcp.NetLibError, c.convert_to_ssl, sni="foo.com", method=tcp.TLSv1_METHOD)


class TestSNI(ServerTestBase):
    @classmethod
    def makeserver(cls):
        return TServer(("127.0.0.1", 0), True, cls.q, SNIHandler)

    def test_echo(self):
        c = tcp.TCPClient("127.0.0.1", self.port)
        c.connect()
        c.convert_to_ssl(sni="foo.com")
        assert c.rfile.readline() == "foo.com"


class TestSSLDisconnect(ServerTestBase):
    @classmethod
    def makeserver(cls):
        return TServer(("127.0.0.1", 0), True, cls.q, DisconnectHandler)

    def test_echo(self):
        c = tcp.TCPClient("127.0.0.1", self.port)
        c.connect()
        c.convert_to_ssl()
        # Excercise SSL.ZeroReturnError
        c.rfile.read(10)
        c.close()
        tutils.raises(tcp.NetLibDisconnect, c.wfile.write, "foo")
        tutils.raises(Queue.Empty, self.q.get_nowait)


class TestDisconnect(ServerTestBase):
    @classmethod
    def makeserver(cls):
        return TServer(("127.0.0.1", 0), False, cls.q, DisconnectHandler)

    def test_echo(self):
        c = tcp.TCPClient("127.0.0.1", self.port)
        c.connect()
        # Excercise SSL.ZeroReturnError
        c.rfile.read(10)
        c.wfile.write("foo")
        c.close()
        c.close()


class TestServerTimeOut(ServerTestBase):
    @classmethod
    def makeserver(cls):
        return TServer(("127.0.0.1", 0), False, cls.q, TimeoutHandler)

    def test_timeout(self):
        c = tcp.TCPClient("127.0.0.1", self.port)
        c.connect()
        time.sleep(0.3)
        assert self.last_handler.timeout


class TestTimeOut(ServerTestBase):
    @classmethod
    def makeserver(cls):
        return TServer(("127.0.0.1", 0), False, cls.q, HangHandler)

    def test_timeout(self):
        c = tcp.TCPClient("127.0.0.1", self.port)
        c.connect()
        c.settimeout(0.1)
        tutils.raises(tcp.NetLibTimeout, c.rfile.read, 10)


class TestSSLTimeOut(ServerTestBase):
    @classmethod
    def makeserver(cls):
        return TServer(("127.0.0.1", 0), True, cls.q, HangHandler)

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
