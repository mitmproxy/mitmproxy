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


class TServer(tcp.TCPServer):
    def __init__(self, addr, ssl, q, handler, v3_only=False):
        tcp.TCPServer.__init__(self, addr)
        self.ssl, self.q = ssl, q
        self.v3_only = v3_only
        self.handler = handler

    def handle_connection(self, request, client_address):
        h = self.handler(request, client_address, self)
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


class TestTimeOut(ServerTestBase):
    @classmethod
    def makeserver(cls):
        return TServer(("127.0.0.1", 0), False, cls.q, HangHandler)

    def test_timeout_client(self):
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
    def test_wrap(self):
        s = cStringIO.StringIO("foobar\nfoobar")
        s = tcp.FileLike(s)
        s.flush()
        assert s.readline() == "foobar\n"
        assert s.readline() == "foobar"
        # Test __getattr__
        assert s.isatty

    def test_limit(self):
        s = cStringIO.StringIO("foobar\nfoobar")
        s = tcp.FileLike(s)
        assert s.readline(3) == "foo"

    def test_limitless(self):
        s = cStringIO.StringIO("f"*(50*1024))
        s = tcp.FileLike(s)
        ret = s.read(-1)
        assert len(ret) == 50 * 1024
