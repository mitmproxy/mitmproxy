from mitmproxy.protocol import (Layer, SocksClientLayer, ServerConnectionMixin)
from mitmproxy.models import ServerConnection
from test.netlib import tservers
from netlib import tcp
from . import tutils


class MockLayer(Layer):

    def __init__(self, port):
        super(MockLayer, self).__init__(self)
        self.server_conn = ServerConnection((u"127.0.0.1", port))

    def set_server(self, address, *args, **kwargs):
        self.server_conn = ServerConnection(address)

    def connect(self):
        self.server_conn.connect()

class TestSocksClientLayer(tservers.SocksServerTestBase):

    def test_set_server(self):
        s = SocksClientLayer(MockLayer(self.port), None)
        assert s.server_conn.address == None
        s.set_server(("0.0.0.0", 0))
        assert s.server_conn.address == tcp.Address(("0.0.0.0", 0))

    def test_change_socks_proxy_server(self):
        s = SocksClientLayer(MockLayer(self.port), None)
        s.change_socks_proxy_server((u"127.0.0.1", self.port))
        assert s.server_conn.via.address == tcp.Address((u"127.0.0.1", self.port))

    def test_connect(self):
        self.setSocksConfig(("test", "test", True))
        s = SocksClientLayer(MockLayer(self.port), None)
        s.change_socks_proxy_server((u"127.0.0.1", self.port), "test", "test")
        s.set_server(("0.0.0.0", 0))
        s.connect()

    def test_conn_fail(self):
        self.setSocksConfig(("test", "test", False))
        s = SocksClientLayer(MockLayer(self.port), None)
        s.change_socks_proxy_server((u"127.0.0.1", self.port), "test", "test")
        tutils.raises("Cannot connect to server, no server address given.", s.connect)
        s.set_server(("0.0.0.0", 0))
        tutils.raises("Server connection to server", s.connect)
