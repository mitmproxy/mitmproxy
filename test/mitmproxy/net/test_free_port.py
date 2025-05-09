import socket

from mitmproxy.net import free_port


def _raise(*_, **__):
    raise OSError


def test_get_free_port():
    assert free_port.get_free_port() is not None


def test_never_raises(monkeypatch):
    monkeypatch.setattr(socket.socket, "bind", _raise)
    assert free_port.get_free_port() == 0
