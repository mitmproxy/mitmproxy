from mitmproxy.options import Options
from mitmproxy.proxy.context import Context
from mitmproxy.proxy.layers.quic._hooks import QuicStartServerHook
from mitmproxy.proxy.layers.quic._hooks import QuicTlsData
from mitmproxy.proxy.layers.quic._hooks import QuicTlsSettings
from mitmproxy.test.tflow import tclient_conn


def test_reprs():
    client = tclient_conn()
    assert repr(
        QuicStartServerHook(
            data=QuicTlsData(
                conn=client,
                context=Context(client, Options()),
                settings=QuicTlsSettings(),
            )
        )
    )
