import pytest

from mitmproxy import flowfilter
from mitmproxy.test import tflow


class TestWebSocketFlow:

    def test_copy(self):
        f = tflow.twebsocketflow()
        f.get_state()
        f2 = f.copy()
        a = f.get_state()
        b = f2.get_state()
        del a["id"]
        del b["id"]
        del a["handshake_flow"]["id"]
        del b["handshake_flow"]["id"]
        assert a == b
        assert not f == f2
        assert f is not f2

        assert f.client_key == f2.client_key
        assert f.client_protocol == f2.client_protocol
        assert f.client_extensions == f2.client_extensions
        assert f.server_accept == f2.server_accept
        assert f.server_protocol == f2.server_protocol
        assert f.server_extensions == f2.server_extensions
        assert f.messages is not f2.messages
        assert f.handshake_flow is not f2.handshake_flow

        for m in f.messages:
            m2 = m.copy()
            m2.set_state(m2.get_state())
            assert m is not m2
            assert m.get_state() == m2.get_state()

        f = tflow.twebsocketflow(err=True)
        f2 = f.copy()
        assert f is not f2
        assert f.handshake_flow is not f2.handshake_flow
        assert f.error.get_state() == f2.error.get_state()
        assert f.error is not f2.error

    def test_match(self):
        f = tflow.twebsocketflow()
        assert not flowfilter.match("~b nonexistent", f)
        assert flowfilter.match(None, f)
        assert not flowfilter.match("~b nonexistent", f)

        f = tflow.twebsocketflow(err=True)
        assert flowfilter.match("~e", f)

        with pytest.raises(ValueError):
            flowfilter.match("~", f)

    def test_repr(self):
        f = tflow.twebsocketflow()
        assert f.message_info(f.messages[0])
        assert 'WebSocketFlow' in repr(f)
        assert 'binary message: ' in repr(f.messages[0])
        assert 'text message: ' in repr(f.messages[1])
