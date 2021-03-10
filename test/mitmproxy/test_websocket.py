from mitmproxy import http
from mitmproxy import websocket
from mitmproxy.test import tflow
from wsproto.frame_protocol import Opcode


class TestWebSocketData:
    def test_repr(self):
        assert repr(tflow.twebsocketflow().websocket) == "<WebSocketData (3 messages)>"

    def test_state(self):
        f = tflow.twebsocketflow()
        f2 = http.HTTPFlow.from_state(f.get_state())
        f2.set_state(f.get_state())


class TestWebSocketMessage:
    def test_basic(self):
        m = websocket.WebSocketMessage(Opcode.TEXT, True, b"foo")
        m.set_state(m.get_state())
        assert m.content == b"foo"
        assert repr(m) == "'foo'"
        m.type = Opcode.BINARY
        assert repr(m) == "b'foo'"

        assert not m.killed
        m.kill()
        assert m.killed
