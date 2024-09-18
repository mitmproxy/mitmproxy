from mitmproxy.proxy.layers.quic._commands import CloseQuicConnection
from mitmproxy.proxy.layers.quic._commands import QuicStreamCommand
from mitmproxy.proxy.layers.quic._commands import ResetQuicStream
from mitmproxy.proxy.layers.quic._commands import SendQuicStreamData
from mitmproxy.proxy.layers.quic._commands import StopSendingQuicStream
from mitmproxy.test.tflow import tclient_conn


def test_reprs():
    client = tclient_conn()
    assert repr(QuicStreamCommand(client, 42))
    assert repr(SendQuicStreamData(client, 42, b"data"))
    assert repr(ResetQuicStream(client, 42, 0xFF))
    assert repr(StopSendingQuicStream(client, 42, 0xFF))
    assert repr(CloseQuicConnection(client, 0xFF, None, "reason"))
