import pytest
from wsproto.frame_protocol import Opcode

from mitmproxy import eventsequence
from mitmproxy import websocket
from mitmproxy.proxy import layers
from mitmproxy.test import tflow


@pytest.mark.parametrize(
    "resp, err",
    [
        (False, False),
        (True, False),
        (False, True),
        (True, True),
    ],
)
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


def test_websocket_flow_control():
    f = tflow.twebsocketflow()
    f.websocket.messages = [
        websocket.WebSocketMessage(Opcode.PING, True, b"ping"),
        websocket.WebSocketMessage(Opcode.TEXT, True, b"hello"),
        websocket.WebSocketMessage(Opcode.CLOSE, False, b"\x03\xe8"),
    ]
    hooks = [type(h) for h in eventsequence.iterate(f)]
    assert hooks[4:] == [
        layers.websocket.WebsocketStartHook,
        layers.websocket.WebsocketControlHook,
        layers.websocket.WebsocketMessageHook,
        layers.websocket.WebsocketControlHook,
        layers.websocket.WebsocketEndHook,
    ]
    assert len(f.websocket.messages) == 3


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


@pytest.mark.parametrize("err", [False, True])
def test_udp_flow(err):
    f = tflow.tudpflow(err=err)
    i = eventsequence.iterate(f)
    assert isinstance(next(i), layers.udp.UdpStartHook)
    assert len(f.messages) == 0
    assert isinstance(next(i), layers.udp.UdpMessageHook)
    assert len(f.messages) == 1
    assert isinstance(next(i), layers.udp.UdpMessageHook)
    assert len(f.messages) == 2
    if err:
        assert isinstance(next(i), layers.udp.UdpErrorHook)
    else:
        assert isinstance(next(i), layers.udp.UdpEndHook)


@pytest.mark.parametrize(
    "resp, err",
    [
        (False, False),
        (True, False),
        (False, True),
        (True, True),
    ],
)
def test_dns(resp, err):
    f = tflow.tdnsflow(resp=resp, err=err)
    i = eventsequence.iterate(f)
    assert isinstance(next(i), layers.dns.DnsRequestHook)
    if resp:
        assert isinstance(next(i), layers.dns.DnsResponseHook)
    if err:
        assert isinstance(next(i), layers.dns.DnsErrorHook)


def test_invalid():
    with pytest.raises(TypeError):
        next(eventsequence.iterate(42))
