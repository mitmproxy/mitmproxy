import pytest

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

        assert not m.dropped
        m.drop()
        assert m.dropped

    def test_text(self):
        txt = websocket.WebSocketMessage(Opcode.TEXT, True, b"foo")
        bin = websocket.WebSocketMessage(Opcode.BINARY, True, b"foo")

        assert txt.is_text
        assert txt.text == "foo"
        txt.text = "bar"
        assert txt.content == b"bar"

        assert not bin.is_text
        with pytest.raises(AttributeError, match="do not have a 'text' attribute."):
            _ = bin.text
        with pytest.raises(AttributeError, match="do not have a 'text' attribute."):
            bin.text = "bar"
