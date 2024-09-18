from mitmproxy.proxy.layers.quic._events import QuicConnectionClosed
from mitmproxy.proxy.layers.quic._events import QuicStreamDataReceived
from mitmproxy.test.tflow import tclient_conn


def test_reprs():
    client = tclient_conn()
    assert repr(QuicStreamDataReceived(client, 42, b"data", end_stream=False))
    assert repr(QuicConnectionClosed(client, 0xFF, None, "reason"))
