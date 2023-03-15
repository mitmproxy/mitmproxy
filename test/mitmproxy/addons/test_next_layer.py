from typing import Optional
from unittest.mock import MagicMock

import pytest

from mitmproxy import connection
from mitmproxy.addons.next_layer import NextLayer
from mitmproxy.proxy.layers.http import HTTPMode
from mitmproxy.proxy import context, layer, layers
from mitmproxy.test import taddons
from mitmproxy.test import tflow


@pytest.fixture
def tctx():
    context.Context(
        connection.Client(("client", 1234), ("127.0.0.1", 8080), 1605699329),
        tctx.options,
    )


client_hello_no_extensions = bytes.fromhex(
    "1603030065"  # record header
    "01000061"  # handshake header
    "03015658a756ab2c2bff55f636814deac086b7ca56b65058c7893ffc6074f5245f70205658a75475103a152637"
    "78e1bb6d22e8bbd5b6b0a3a59760ad354e91ba20d353001a0035002f000a000500040009000300060008006000"
    "61006200640100"
)
client_hello_with_extensions = bytes.fromhex(
    "16030300bb"  # record layer
    "010000b7"  # handshake layer
    "03033b70638d2523e1cba15f8364868295305e9c52aceabda4b5147210abc783e6e1000022c02bc02fc02cc030"
    "cca9cca8cc14cc13c009c013c00ac014009c009d002f0035000a0100006cff0100010000000010000e00000b65"
    "78616d706c652e636f6d0017000000230000000d00120010060106030501050304010403020102030005000501"
    "00000000001200000010000e000c02683208687474702f312e3175500000000b00020100000a00080006001d00"
    "170018"
)


dtls_client_hello_with_extensions = bytes.fromhex(
    "16fefd00000000000000000085"    # record layer
    "010000790000000000000079"      # handshake layer
    "fefd62bf0e0bf809df43e7669197be831919878b1a72c07a584d3c0a8ca6665878010000000cc02bc02fc00ac014c02cc0"
    "3001000043000d0010000e0403050306030401050106010807ff01000100000a00080006001d00170018000b00020100001"
    "7000000000010000e00000b6578616d706c652e636f6d"
)


class TestNextLayer:
    def test_configure(self):
        nl = NextLayer()
        with taddons.context(nl) as tctx:
            with pytest.raises(Exception, match="mutually exclusive"):
                tctx.configure(
                    nl, allow_hosts=["example.org"], ignore_hosts=["example.com"]
                )

    def test_ignore_connection(self):
        nl = NextLayer()
        with taddons.context(nl) as tctx:
            assert not nl.ignore_connection(("example.com", 443), b"")

            tctx.configure(nl, ignore_hosts=["example.com"])
            assert nl.ignore_connection(("example.com", 443), b"")
            assert nl.ignore_connection(("example.com", 1234), b"")
            assert nl.ignore_connection(("com", 443), b"") is False
            assert nl.ignore_connection(None, b"") is False
            assert nl.ignore_connection(None, client_hello_no_extensions) is False
            assert nl.ignore_connection(None, client_hello_with_extensions)
            assert nl.ignore_connection(None, client_hello_with_extensions[:-5]) is None
            # invalid clienthello
            assert (
                nl.ignore_connection(
                    None, client_hello_no_extensions[:9] + b"\x00" * 200
                )
                is False
            )
            # different server name and SNI
            assert nl.ignore_connection(("decoy", 1234), client_hello_with_extensions)

            tctx.configure(nl, ignore_hosts=[], allow_hosts=["example.com"])
            assert nl.ignore_connection(("example.com", 443), b"") is False
            assert nl.ignore_connection(("example.org", 443), b"")
            # different server name and SNI
            assert (
                nl.ignore_connection(("decoy", 1234), client_hello_with_extensions)
                is False
            )

    def test_next_layer(self, monkeypatch):
        ctx = MagicMock()
        ctx.client.transport_protocol = "tcp"
        nl_layer = layer.NextLayer(ctx)
        monkeypatch.setattr(nl_layer, "data_client", lambda: b"\x16\x03\x03")
        nl = NextLayer()

        with taddons.context(nl):
            nl.next_layer(nl_layer)
            assert nl_layer.layer

    def test_next_layer2(self):
        nl = NextLayer()
        ctx = MagicMock()
        ctx.client.alpn = None
        ctx.server.address = ("example.com", 443)
        ctx.client.transport_protocol = "tcp"
        with taddons.context(nl) as tctx:
            ctx.layers = [layers.modes.HttpProxy(ctx)]

            assert nl._next_layer(ctx, b"", b"") is None

            tctx.configure(nl, ignore_hosts=["example.com"])
            assert isinstance(nl._next_layer(ctx, b"123", b""), layers.TCPLayer)
            assert nl._next_layer(ctx, client_hello_no_extensions[:10], b"") is None

            tctx.configure(nl, ignore_hosts=[])
            assert isinstance(
                nl._next_layer(ctx, client_hello_no_extensions, b""),
                layers.ServerTLSLayer,
            )
            assert isinstance(ctx.layers[-1], layers.ClientTLSLayer)

            ctx.layers = [layers.modes.HttpProxy(ctx)]
            assert isinstance(
                nl._next_layer(ctx, client_hello_no_extensions, b""),
                layers.ClientTLSLayer,
            )

            ctx.layers = [layers.modes.HttpProxy(ctx)]
            assert isinstance(
                nl._next_layer(ctx, b"GET http://example.com/ HTTP/1.1\r\n", b""),
                layers.HttpLayer,
            )
            assert ctx.layers[-1].mode == HTTPMode.regular

            ctx.layers = [layers.modes.HttpUpstreamProxy(ctx)]
            assert isinstance(
                nl._next_layer(ctx, b"GET http://example.com/ HTTP/1.1\r\n", b""),
                layers.HttpLayer,
            )
            assert ctx.layers[-1].mode == HTTPMode.upstream

            tctx.configure(nl, tcp_hosts=["example.com"])
            assert isinstance(nl._next_layer(ctx, b"123", b""), layers.TCPLayer)

            tctx.configure(nl, tcp_hosts=[])
            assert isinstance(nl._next_layer(ctx, b"GET /foo", b""), layers.HttpLayer)
            assert isinstance(nl._next_layer(ctx, b"", b"hello"), layers.TCPLayer)

    def test_next_layer_udp(self):
        def is_ignored_udp(layer: Optional[layer.Layer]):
            return isinstance(layer, layers.UDPLayer) and layer.flow is None

        def is_intercepted_udp(layer: Optional[layer.Layer]):
            return isinstance(layer, layers.UDPLayer) and layer.flow is not None

        nl = NextLayer()
        ctx = MagicMock()
        ctx.client.alpn = None
        ctx.server.address = ("example.com", 443)
        ctx.client.transport_protocol = "udp"
        with taddons.context(nl) as tctx:
            ctx.layers = [layers.modes.HttpProxy(ctx)]
            tctx.configure(nl, rawudp=False)
            assert is_ignored_udp(nl._next_layer(ctx, b"", b""))

            ctx.layers = [layers.modes.HttpProxy(ctx)]
            tctx.configure(nl, rawudp=True)
            assert is_intercepted_udp(nl._next_layer(ctx, b"", b""))

            ctx.layers = [layers.modes.HttpProxy(ctx)]
            ctx.server.address = ("nomatch.com", 443)
            tctx.configure(nl, ignore_hosts=["example.com"])
            assert is_intercepted_udp(nl._next_layer(ctx, dtls_client_hello_with_extensions[:50], b""))
            assert is_ignored_udp(nl._next_layer(ctx, dtls_client_hello_with_extensions, b""))

            ctx.layers = [layers.modes.HttpProxy(ctx)]
            ctx.server.address = ("example.com", 443)
            assert is_ignored_udp(nl._next_layer(ctx, dtls_client_hello_with_extensions[:50], b""))

            ctx.layers = [layers.modes.HttpProxy(ctx)]
            tctx.configure(nl, ignore_hosts=[])
            assert isinstance(nl._next_layer(ctx, dtls_client_hello_with_extensions, b""), layers.ClientTLSLayer)

            ctx.layers = [layers.modes.HttpProxy(ctx)]
            tctx.configure(nl, udp_hosts=["example.com"])
            assert isinstance(nl._next_layer(ctx, tflow.tdnsreq().packed, b""), layers.UDPLayer)

            ctx.layers = [layers.modes.HttpProxy(ctx)]
            tctx.configure(nl, udp_hosts=[])
            assert isinstance(nl._next_layer(ctx, tflow.tdnsreq().packed, b""), layers.DNSLayer)

    def test_next_layer_invalid_proto(self):
        nl = NextLayer()
        ctx = MagicMock()
        ctx.client.transport_protocol = "invalid"
        with taddons.context(nl):
            with pytest.raises(AssertionError):
                nl._next_layer(ctx, b"", b"")
