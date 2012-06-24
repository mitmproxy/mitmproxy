import cStringIO, threading, Queue
from netlib import tcp
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
        cls.server = ServerThread(cls.makeserver())
        cls.server.start()

    @classmethod
    def teardownAll(cls):
        cls.server.shutdown()


class THandler(tcp.BaseHandler):
    def handle(self):
        if self.server.ssl:
            self.convert_to_ssl(
                tutils.test_data.path("data/server.crt"),
                tutils.test_data.path("data/server.key"),
            )
        v = self.rfile.readline()
        if v.startswith("echo"):
            self.wfile.write(v)
        elif v.startswith("error"):
            raise ValueError("Testing an error.")
        self.wfile.flush()


class TServer(tcp.TCPServer):
    def __init__(self, addr, ssl, q):
        tcp.TCPServer.__init__(self, addr)
        self.ssl, self.q = ssl, q

    def handle_connection(self, request, client_address):
        THandler(request, client_address, self)

    def handle_error(self, request, client_address):
        s = cStringIO.StringIO()
        tcp.TCPServer.handle_error(self, request, client_address, s)
        self.q.put(s.getvalue())


class TestServer(ServerTestBase):
    @classmethod
    def makeserver(cls):
        cls.q = Queue.Queue()
        s = TServer(("127.0.0.1", 0), False, cls.q)
        cls.port = s.port
        return s

    def test_echo(self):
        testval = "echo!\n"
        c = tcp.TCPClient(False, "127.0.0.1", self.port, None, None)
        c.wfile.write(testval)
        c.wfile.flush()
        assert c.rfile.readline() == testval


class TestServerSSL(ServerTestBase):
    @classmethod
    def makeserver(cls):
        cls.q = Queue.Queue()
        s = TServer(("127.0.0.1", 0), True, cls.q)
        cls.port = s.port
        return s

    def test_echo(self):
        c = tcp.TCPClient(True, "127.0.0.1", self.port, None, None)
        testval = "echo!\n"
        c.wfile.write(testval)
        c.wfile.flush()
        assert c.rfile.readline() == testval


class TestTCPClient:
    def test_conerr(self):
        tutils.raises(tcp.NetLibError, tcp.TCPClient, False, "127.0.0.1", 0, None, None)


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
