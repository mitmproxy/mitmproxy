from hypothesis import given
from hypothesis.strategies import binary

from . import full_eval
from mitmproxy.contentviews.socketio import EngineIO
from mitmproxy.contentviews.socketio import format_packet
from mitmproxy.contentviews.socketio import parse_packet
from mitmproxy.contentviews.socketio import SocketIO
from mitmproxy.contentviews.socketio import ViewSocketIO
from mitmproxy.test import tflow


def test_parse_packet():
    assert parse_packet(b"0payload") == (EngineIO.OPEN, b"payload")
    assert parse_packet(b"40") == (SocketIO.CONNECT, b"")
    assert parse_packet(b"40payload") == (SocketIO.CONNECT, b"payload")


def test_format_packet():
    assert list(format_packet(SocketIO.EVENT, b"data")[1]) == [
        [
            ("content_none", "SocketIO.EVENT "),
            ("text", b"data"),
        ],
    ]
    assert not list(format_packet(EngineIO.PING, b"")[1])
    assert not list(format_packet(SocketIO.ACK, b"")[1])


def test_view():
    v = full_eval(ViewSocketIO())
    assert not v(b"HTTP/1.1")
    assert not v(b"GET")
    assert v(b"0")
    assert v(b"6")
    assert v(b"40")
    assert not v(b"4")
    assert v(b"42")
    assert v(b"42eventdata")


@given(binary())
def test_view_doesnt_crash(data):
    v = full_eval(ViewSocketIO())
    v(data)


def test_render_priority():
    v = ViewSocketIO()
    assert not v.render_priority(b"")

    flow = tflow.twebsocketflow()
    assert not v.render_priority(b"", flow=flow)
    assert not v.render_priority(b"message", flow=flow)

    flow.request.path = b"/asdf/socket.io/?..."
    assert v.render_priority(b"message", flow=flow)
    assert not v.render_priority(b"", flow=flow)
