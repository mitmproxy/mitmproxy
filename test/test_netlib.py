import cStringIO, threading, Queue
from libmproxy import netlib
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


class THandler(netlib.BaseHandler):
    def handle(self):
        v = self.rfile.readline()
        if v.startswith("echo"):
            self.wfile.write(v)
        elif v.startswith("error"):
            raise ValueError("Testing an error.")
        self.wfile.flush()


class TServer(netlib.TCPServer):
    def __init__(self, addr, q):
        netlib.TCPServer.__init__(self, addr)
        self.q = q

    def handle_connection(self, request, client_address):
        THandler(request, client_address, self)

    def handle_error(self, request, client_address):
        s = cStringIO.StringIO()
        netlib.TCPServer.handle_error(self, request, client_address, s)
        self.q.put(s.getvalue())


class TestServer(ServerTestBase):
    @classmethod
    def makeserver(cls):
        cls.q = Queue.Queue()
        s = TServer(("127.0.0.1", 0), cls.q)
        cls.port = s.port
        return s

    def test_echo(self):
        testval = "echo!\n"
        c = netlib.TCPClient(False, "127.0.0.1", self.port, None)
        c.wfile.write(testval)
        c.wfile.flush()
        assert c.rfile.readline() == testval

    def test_error(self):
        testval = "error!\n"
        c = netlib.TCPClient(False, "127.0.0.1", self.port, None)
        c.wfile.write(testval)
        c.wfile.flush()
        assert "Testing an error" in self.q.get()



class TestTCPClient:
    def test_conerr(self):
        tutils.raises(netlib.NetLibError, netlib.TCPClient, False, "127.0.0.1", 0, None)


class TestFileLike:
    def test_wrap(self):
        s = cStringIO.StringIO("foobar\nfoobar")
        s = netlib.FileLike(s)
        s.flush()
        assert s.readline() == "foobar\n"
        assert s.readline() == "foobar"
        # Test __getattr__
        assert s.isatty

    def test_limit(self):
        s = cStringIO.StringIO("foobar\nfoobar")
        s = netlib.FileLike(s)
        assert s.readline(3) == "foo"

