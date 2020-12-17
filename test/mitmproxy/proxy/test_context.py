from mitmproxy.proxy import context
from mitmproxy.test import tflow, taddons


class TestConnection:
    def test_basic(self):
        c = context.Client(
            ("127.0.0.1", 52314),
            ("127.0.0.1", 8080),
            1607780791
        )
        assert not c.tls_established
        c.timestamp_tls_setup = 1607780792
        assert c.tls_established
        assert c.connected
        c.state = context.ConnectionState.CAN_WRITE
        assert not c.connected

    def test_eq(self):
        c = tflow.tclient_conn()
        c2 = c.copy()
        assert c == c
        assert c != c2
        assert c != 42
        assert hash(c) != hash(c2)

        c2.id = c.id
        assert c == c2


class TestClient:
    def test_basic(self):
        c = context.Client(
            ("127.0.0.1", 52314),
            ("127.0.0.1", 8080),
            1607780791
        )
        assert repr(c)

    def test_state(self):
        c = tflow.tclient_conn()
        assert context.Client.from_state(c.get_state()).get_state() == c.get_state()

        c2 = tflow.tclient_conn()
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
        s = context.Server(("address", 22))
        assert repr(s)

    def test_state(self):
        c = tflow.tserver_conn()
        c2 = c.copy()
        assert c2.get_state() != c.get_state()
        c.id = c2.id = "foo"
        assert c2.get_state() == c.get_state()


def test_context():
    with taddons.context() as tctx:
        c = context.Context(
            tflow.tclient_conn(),
            tctx.options
        )
        assert repr(c)
        c.layers.append(1)
        c2 = c.fork()
        c.layers.append(2)
        c2.layers.append(3)
        assert c.layers == [1, 2]
        assert c2.layers == [1, 3]
