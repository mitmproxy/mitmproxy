import threading
from mitmproxy.protocol import (Layer, SocksClientLayer, ServerConnectionMixin)
from mitmproxy.models import ServerConnection
from test.netlib import tservers
from netlib import tcp
from . import tutils
from twisted.internet import reactor, threads
from twunnel import local_proxy_server


class _SocksServer(threading.Thread):

    def __init__(self):
        threading.Thread.__init__(self)
        configuration = {
            "PROXY_SERVERS": [],
            "LOCAL_PROXY_SERVER": {
                "TYPE": "SOCKS5",
                "ADDRESS": "127.0.0.1",
                "PORT": 0
            },
            "REMOTE_PROXY_SERVERS": []
        }
        self.socks_server = local_proxy_server.createPort(configuration)
        self.socks_server.startListening()
        self.port = self.socks_server._realPortNumber

    def run(self):
        reactor.run(installSignalHandlers=0)

    def stop_proxy(self):
        self.socks_server.stopListening()
        threads.blockingCallFromThread(reactor, reactor.stop)


class SocksServerTestBase(tservers.ServerTestBase):

    @classmethod
    def setup_class(cls):
        super(SocksServerTestBase, cls).setup_class()
        cls.proxy_server = _SocksServer()
        cls.proxy_port = cls.proxy_server.port
        cls.proxy_server.start()

    @classmethod
    def teardown_class(cls):
        super(SocksServerTestBase, cls).teardown_class()
        cls.proxy_server.stop_proxy()

class EchoHandler(tcp.BaseHandler):
    sni = None

    def handle_sni(self, connection):
        self.sni = connection.get_servername()

    def handle(self):
        v = self.rfile.readline()
        self.wfile.write(v)
        self.wfile.flush()

class MockLayer(Layer):

    def __init__(self, port):
        super(MockLayer, self).__init__(self)
        self.server_conn = ServerConnection((u"127.0.0.1", port))

    def set_server(self, address, *args, **kwargs):
        self.server_conn = ServerConnection(address)

    def connect(self):
        self.server_conn.connect()

class TestSocksClientLayer(SocksServerTestBase):
    handler = EchoHandler

    def test_set_server(self):
        s = SocksClientLayer(MockLayer(0), None)
        assert s.server_conn.address == None
        s.set_server(("0.0.0.0", 0))
        assert s.server_conn.address == tcp.Address(("0.0.0.0", 0))

    def test_change_socks_proxy_server(self):
        s = SocksClientLayer(MockLayer(0), None)
        s.change_socks_proxy_server((u"127.0.0.1", self.port))
        assert s.server_conn.via.address == tcp.Address((u"127.0.0.1", self.port))

    def test_connect(self):
        s = SocksClientLayer(MockLayer(0), None)
        s.change_socks_proxy_server((u"127.0.0.1", self.proxy_port))
        s.set_server(("127.0.0.1", self.port))
        s.connect()
        testval = "echo\n"
        s.server_conn.wfile.write(testval)
        s.server_conn.wfile.flush()
        assert s.server_conn.rfile.readline() == testval

    def test_conn_fail(self):
        s = SocksClientLayer(MockLayer(0), None)
        s.change_socks_proxy_server((u"127.0.0.1", self.proxy_port))
        tutils.raises("Cannot connect to server, no server address given.", s.connect)
