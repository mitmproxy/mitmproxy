import pytest

from mitmproxy.contentviews import Metadata
from mitmproxy.contentviews._view_socketio import EngineIO
from mitmproxy.contentviews._view_socketio import parse_packet
from mitmproxy.contentviews._view_socketio import socket_io
from mitmproxy.contentviews._view_socketio import SocketIO
from mitmproxy.test import tflow


def test_parse_packet():
    assert parse_packet(b"0payload") == (EngineIO.OPEN, b"payload")
    assert parse_packet(b"40") == (SocketIO.CONNECT, b"")
    assert parse_packet(b"40payload") == (SocketIO.CONNECT, b"payload")


def test_view():
    with pytest.raises(Exception):
        socket_io.prettify(b"HTTP/1.1", Metadata())
    with pytest.raises(Exception):
        socket_io.prettify(b"GET", Metadata())
    assert socket_io.prettify(b"0", Metadata())
    assert socket_io.prettify(b"6", Metadata())
    assert socket_io.prettify(b"40", Metadata())
    with pytest.raises(Exception):
        socket_io.prettify(b"4", Metadata())
    assert socket_io.prettify(b"42", Metadata())
    assert socket_io.prettify(b"42eventdata", Metadata())
    assert socket_io.prettify(b"2", Metadata()) == ""


def test_render_priority():
    assert not socket_io.render_priority(b"", Metadata())

    flow = tflow.twebsocketflow()
    assert not socket_io.render_priority(b"", Metadata(flow=flow))
    assert not socket_io.render_priority(b"message", Metadata(flow=flow))

    flow.request.path = b"/asdf/socket.io/?..."
    assert socket_io.render_priority(b"message", Metadata(flow=flow))
    assert not socket_io.render_priority(b"", Metadata(flow=flow))
