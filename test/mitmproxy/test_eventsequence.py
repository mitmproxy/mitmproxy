import pytest

from mitmproxy import eventsequence
from mitmproxy.proxy import layers
from mitmproxy.test import tflow


@pytest.mark.parametrize("resp, err", [
    (False, False),
    (True, False),
    (False, True),
    (True, True),
])
def test_http_flow(resp, err):
    f = tflow.tflow(resp=resp, err=err)
    i = eventsequence.iterate(f)
    assert isinstance(next(i), layers.http.HttpRequestHeadersHook)
    assert isinstance(next(i), layers.http.HttpRequestHook)
    if resp:
        assert isinstance(next(i), layers.http.HttpResponseHeadersHook)
        assert isinstance(next(i), layers.http.HttpResponseHook)
    if err:
        assert isinstance(next(i), layers.http.HttpErrorHook)


def test_websocket_flow():
    f = tflow.twebsocketflow()
    i = eventsequence.iterate(f)

    assert isinstance(next(i), layers.http.HttpRequestHeadersHook)
    assert isinstance(next(i), layers.http.HttpRequestHook)
    assert isinstance(next(i), layers.http.HttpResponseHeadersHook)
    assert isinstance(next(i), layers.http.HttpResponseHook)

    assert isinstance(next(i), layers.websocket.WebsocketStartHook)
    assert len(f.websocket.messages) == 0
    assert isinstance(next(i), layers.websocket.WebsocketMessageHook)
    assert len(f.websocket.messages) == 1
    assert isinstance(next(i), layers.websocket.WebsocketMessageHook)
    assert len(f.websocket.messages) == 2
    assert isinstance(next(i), layers.websocket.WebsocketMessageHook)
    assert len(f.websocket.messages) == 3
    assert isinstance(next(i), layers.websocket.WebsocketEndHook)


@pytest.mark.parametrize("err", [False, True])
def test_tcp_flow(err):
    f = tflow.ttcpflow(err=err)
    i = eventsequence.iterate(f)
    assert isinstance(next(i), layers.tcp.TcpStartHook)
    assert len(f.messages) == 0
    assert isinstance(next(i), layers.tcp.TcpMessageHook)
    assert len(f.messages) == 1
    assert isinstance(next(i), layers.tcp.TcpMessageHook)
    assert len(f.messages) == 2
    if err:
        assert isinstance(next(i), layers.tcp.TcpErrorHook)
    else:
        assert isinstance(next(i), layers.tcp.TcpEndHook)


def test_invalid():
    with pytest.raises(TypeError):
        next(eventsequence.iterate(42))
