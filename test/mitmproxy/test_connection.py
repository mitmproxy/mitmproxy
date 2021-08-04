import pytest

from mitmproxy.connection import Server, Client, ConnectionState
from mitmproxy.test.tflow import tclient_conn, tserver_conn


class TestConnection:
    def test_basic(self):
        c = Client(
            ("127.0.0.1", 52314),
            ("127.0.0.1", 8080),
            1607780791
        )
        assert not c.tls_established
        c.timestamp_tls_setup = 1607780792
        assert c.tls_established
        assert c.connected
        c.state = ConnectionState.CAN_WRITE
        assert not c.connected

    def test_eq(self):
        c = tclient_conn()
        c2 = c.copy()
        assert c == c
        assert c != c2
        assert c != 42
        assert hash(c) != hash(c2)

        c2.id = c.id
        assert c == c2


class TestClient:
    def test_basic(self):
        c = Client(
            ("127.0.0.1", 52314),
            ("127.0.0.1", 8080),
            1607780791
        )
        assert repr(c)
        assert str(c)
        c.timestamp_tls_setup = 1607780791
        assert str(c)
        c.alpn = b"foo"
        assert str(c) == "Client(127.0.0.1:52314, state=open, alpn=foo)"

    def test_state(self):
        c = tclient_conn()
        assert Client.from_state(c.get_state()).get_state() == c.get_state()

        c2 = tclient_conn()
        assert c != c2

        c2.timestamp_start = 42
        c.set_state(c2.get_state())
        assert c.timestamp_start == 42

        c3 = c.copy()
        assert c3.get_state() != c.get_state()
        c.id = c3.id = "foo"
        assert c3.get_state() == c.get_state()


class TestServer:
    def test_basic(self):
        s = Server(("address", 22))
        assert repr(s)
        assert str(s)
        s.timestamp_tls_setup = 1607780791
        assert str(s)
        s.alpn = b"foo"
        s.sockname = ("127.0.0.1", 54321)
        assert str(s) == "Server(address:22, state=closed, alpn=foo, src_port=54321)"

    def test_state(self):
        c = tserver_conn()
        c2 = c.copy()
        assert c2.get_state() != c.get_state()
        c.id = c2.id = "foo"
        assert c2.get_state() == c.get_state()

    def test_address(self):
        s = Server(("address", 22))
        s.address = ("example.com", 443)
        s.state = ConnectionState.OPEN
        with pytest.raises(RuntimeError):
            s.address = ("example.com", 80)
        # No-op assignment, allowed because it might be triggered by a Server.set_state() call.
        s.address = ("example.com", 443)
