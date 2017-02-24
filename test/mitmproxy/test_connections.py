from unittest import mock

from mitmproxy import connections
from mitmproxy import exceptions
from mitmproxy.net.http import http1
from mitmproxy.test import tflow
from pathod import test


class TestClientConnection:
    def test_state(self):
        c = tflow.tclient_conn()
        assert connections.ClientConnection.from_state(c.get_state()).get_state() == \
            c.get_state()

        c2 = tflow.tclient_conn()
        c2.address = (c2.address[0], 4242)
        assert not c == c2

        c2.timestamp_start = 42
        c.set_state(c2.get_state())
        assert c.timestamp_start == 42

        c3 = c.copy()
        assert c3.get_state() == c.get_state()

        assert str(c)


class TestServerConnection:

    def test_simple(self):
        self.d = test.Daemon()
        sc = connections.ServerConnection((self.d.IFACE, self.d.port))
        sc.connect()
        f = tflow.tflow()
        f.server_conn = sc
        f.request.path = "/p/200:da"

        # use this protocol just to assemble - not for actual sending
        sc.wfile.write(http1.assemble_request(f.request))
        sc.wfile.flush()

        assert http1.read_response(sc.rfile, f.request, 1000)
        assert self.d.last_log()

        sc.finish()
        self.d.shutdown()

    def test_terminate_error(self):
        self.d = test.Daemon()
        sc = connections.ServerConnection((self.d.IFACE, self.d.port))
        sc.connect()
        sc.connection = mock.Mock()
        sc.connection.recv = mock.Mock(return_value=False)
        sc.connection.flush = mock.Mock(side_effect=exceptions.TcpDisconnect)
        sc.finish()
        self.d.shutdown()

    def test_repr(self):
        sc = tflow.tserver_conn()
        assert "address:22" in repr(sc)
        assert "ssl" not in repr(sc)
        sc.ssl_established = True
        assert "ssl" in repr(sc)
        sc.sni = "foo"
        assert "foo" in repr(sc)
