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


quic_client_hello = bytes.fromhex(
    "ca0000000108c0618c84b54541320823fcce946c38d8210044e6a93bbb283593f75ffb6f2696b16cfdcb5b1255"
    "577b2af5fc5894188c9568bc65eef253faf7f0520e41341cfa81d6aae573586665ce4e1e41676364820402feec"
    "a81f3d22dbb476893422069066104a43e121c951a08c53b83f960becf99cf5304d5bc5346f52f472bd1a04d192"
    "0bae025064990d27e5e4c325ac46121d3acadebe7babdb96192fb699693d65e2b2e21c53beeb4f40b50673a2f6"
    "c22091cb7c76a845384fedee58df862464d1da505a280bfef91ca83a10bebbcb07855219dbc14aecf8a48da049"
    "d03c77459b39d5355c95306cd03d6bdb471694fa998ca3b1f875ce87915b88ead15c5d6313a443f39aad808922"
    "57ddfa6b4a898d773bb6fb520ede47ebd59d022431b1054a69e0bbbdf9f0fb32fc8bcc4b6879dd8cd5389474b1"
    "99e18333e14d0347740a11916429a818bb8d93295d36e99840a373bb0e14c8b3adcf5e2165e70803f15316fd5e"
    "5eeec04ae68d98f1adb22c54611c80fcd8ece619dbdf97b1510032ec374b7a71f94d9492b8b8cb56f56556dd97"
    "edf1e50fa90e868ff93636a365678bdf3ee3f8e632588cd506b6f44fbfd4d99988238fbd5884c98f6a124108c1"
    "878970780e42b111e3be6215776ef5be5a0205915e6d720d22c6a81a475c9e41ba94e4983b964cb5c8e1f40607"
    "76d1d8d1adcef7587ea084231016bd6ee2643d11a3a35eb7fe4cca2b3f1a4b21e040b0d426412cca6c4271ea63"
    "fb54ed7f57b41cd1af1be5507f87ea4f4a0c997367e883291de2f1b8a49bdaa52bae30064351b1139703400730"
    "18a4104344ec6b4454b50a42e804bc70e78b9b3c82497273859c82ed241b643642d76df6ceab8f916392113a62"
    "b231f228c7300624d74a846bec2f479ab8a8c3461f91c7bf806236e3bd2f54ba1ef8e2a1e0bfdde0c5ad227f7d"
    "364c52510b1ade862ce0c8d7bd24b6d7d21c99b34de6d177eb3d575787b2af55060d76d6c2060befbb7953a816"
    "6f66ad88ecf929dbb0ad3a16cf7dfd39d925e0b4b649c6d0c07ad46ed0229c17fb6a1395f16e1b138aab3af760"
    "2b0ac762c4f611f7f3468997224ffbe500a7c53f92f65e41a3765a9f1d7e3f78208f5b4e147962d8c97d6c1a80"
    "91ffc36090b2043d71853616f34c2185dc883c54ab6d66e10a6c18e0b9a4742597361f8554a42da3373241d0c8"
    "54119bfadccffaf2335b2d97ffee627cb891bda8140a39399f853da4859f7e19682e152243efbaffb662edd19b"
    "3819a74107c7dbe05ecb32e79dcdb1260f153b1ef133e978ccca3d9e400a7ed6c458d77e2956d2cb897b7a298b"
    "fe144b5defdc23dfd2adf69f1fb0917840703402d524987ae3b1dcb85229843c9a419ef46e1ba0ba7783f2a2ec"
    "d057a57518836aef2a7839ebd3688da98b54c942941f642e434727108d59ea25875b3050ca53d4637c76cbcbb9"
    "e972c2b0b781131ee0a1403138b55486fe86bbd644920ee6aa578e3bab32d7d784b5c140295286d90c99b14823"
    "1487f7ea64157001b745aa358c9ea6bec5a8d8b67a7534ec1f7648ff3b435911dfc3dff798d32fbf2efe2c1fcc"
    "278865157590572387b76b78e727d3e7682cb501cdcdf9a0f17676f99d9aa67f10edccc9a92080294e88bf28c2"
    "a9f32ae535fdb27fff7706540472abb9eab90af12b2bea005da189874b0ca69e6ae1690a6f2adf75be3853c94e"
    "fd8098ed579c20cb37be6885d8d713af4ba52958cee383089b98ed9cb26e11127cf88d1b7d254f15f7903dd7ed"
    "297c0013924e88248684fe8f2098326ce51aa6e5"
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

    @pytest.mark.parametrize(
        ("client_hello", "client_layer", "server_layer"),
        [
            (dtls_client_hello_with_extensions, layers.ClientTLSLayer, layers.ServerTLSLayer),
            (quic_client_hello, layers.ClientQuicLayer, layers.ServerQuicLayer),
        ]
    )
    def test_next_layer_udp(
        self,
        client_hello: bytes,
        client_layer: layer.Layer,
        server_layer: layer.Layer,
    ):
        def is_ignored_udp(layer: Optional[layer.Layer]):
            return isinstance(layer, layers.UDPLayer) and layer.flow is None

        def is_intercepted_udp(layer: Optional[layer.Layer]):
            return isinstance(layer, layers.UDPLayer) and layer.flow is not None

        def is_http(layer: Optional[layer.Layer], mode: HTTPMode):
            return (
                isinstance(layer, layers.HttpLayer)
                and layer.mode is mode
            )

        nl = NextLayer()
        ctx = MagicMock()
        ctx.client.alpn = None
        ctx.server.address = ("example.com", 443)
        ctx.client.transport_protocol = "udp"
        with taddons.context(nl) as tctx:
            ctx.layers = [layers.modes.HttpProxy(ctx), client_layer(ctx)]
            assert is_http(nl._next_layer(ctx, b"", b""), HTTPMode.regular)

            ctx.layers = [layers.modes.HttpUpstreamProxy(ctx), client_layer(ctx)]
            assert is_http(nl._next_layer(ctx, b"", b""), HTTPMode.upstream)

            ctx.layers = [layers.modes.TransparentProxy(ctx)]
            is_intercepted_udp(nl._next_layer(ctx, b"", b""))

            ctx.layers = [layers.modes.TransparentProxy(ctx)]
            ctx.server.address = ("nomatch.com", 443)
            tctx.configure(nl, ignore_hosts=["example.com"])
            assert is_intercepted_udp(nl._next_layer(ctx, client_hello[:50], b""))
            assert is_ignored_udp(nl._next_layer(ctx, client_hello, b""))

            ctx.layers = [layers.modes.TransparentProxy(ctx)]
            ctx.server.address = ("example.com", 443)
            assert is_ignored_udp(nl._next_layer(ctx, client_hello[:50], b""))

            ctx.layers = [layers.modes.TransparentProxy(ctx)]
            tctx.configure(nl, ignore_hosts=[])
            decision = nl._next_layer(ctx, client_hello, b"")
            assert isinstance(decision, server_layer)
            assert isinstance(decision.child_layer, client_layer)

            ctx.layers = [layers.modes.ReverseProxy(ctx), server_layer(ctx)]
            tctx.configure(nl, ignore_hosts=[])
            assert isinstance(nl._next_layer(ctx, client_hello, b""), client_layer)

            ctx.layers = [layers.modes.TransparentProxy(ctx)]
            tctx.configure(nl, udp_hosts=["example.com"])
            assert isinstance(nl._next_layer(ctx, tflow.tdnsreq().packed, b""), layers.UDPLayer)

            ctx.layers = [layers.modes.TransparentProxy(ctx)]
            tctx.configure(nl, udp_hosts=[])
            assert isinstance(nl._next_layer(ctx, tflow.tdnsreq().packed, b""), layers.DNSLayer)

    def test_next_layer_reverse_raw(self):
        nl = NextLayer()
        ctx = MagicMock()
        ctx.client.alpn = None
        ctx.server.address = ("example.com", 443)
        ctx.client.transport_protocol = "udp"
        with taddons.context(nl) as tctx:
            tctx.configure(nl, ignore_hosts=["example.com"])

            ctx.layers = [layers.modes.HttpProxy(ctx), layers.ClientQuicLayer(ctx)]
            decision = nl._next_layer(ctx, b"", b"")
            assert isinstance(decision, layers.ServerQuicLayer)
            assert isinstance(decision.child_layer, layers.RawQuicLayer)

            ctx.layers = [layers.modes.ReverseProxy(ctx), layers.ServerQuicLayer(ctx), layers.ClientQuicLayer(ctx)]
            assert isinstance(nl._next_layer(ctx, b"", b""), layers.RawQuicLayer)

            ctx.layers = [layers.modes.ReverseProxy(ctx), layers.ServerQuicLayer(ctx)]
            decision = nl._next_layer(ctx, b"", b"")
            assert isinstance(decision, layers.ClientQuicLayer)
            assert isinstance(decision.child_layer, layers.RawQuicLayer)

            tctx.configure(nl, ignore_hosts=[])

    def test_next_layer_reverse_quic_mode(self):
        nl = NextLayer()
        ctx = MagicMock()
        ctx.client.alpn = None
        ctx.server.address = ("example.com", 443)
        ctx.client.transport_protocol = "udp"
        ctx.client.proxy_mode.scheme = "quic"
        ctx.layers = [
            layers.modes.ReverseProxy(ctx),
            layers.ServerQuicLayer(ctx),
            layers.ClientQuicLayer(ctx),
        ]
        assert isinstance(nl._next_layer(ctx, b"", b""), layers.RawQuicLayer)
        ctx.layers = [
            layers.modes.ReverseProxy(ctx),
            layers.ServerQuicLayer(ctx),
        ]
        assert nl._next_layer(ctx, b"", b"") is None
        assert isinstance(nl._next_layer(ctx, b"notahandshake", b""), layers.UDPLayer)
        ctx.layers = [
            layers.modes.ReverseProxy(ctx),
            layers.ServerQuicLayer(ctx),
        ]
        assert isinstance(nl._next_layer(ctx, quic_client_hello, b""), layers.ClientQuicLayer)

    def test_next_layer_reverse_http3_mode(self):
        nl = NextLayer()
        ctx = MagicMock()
        ctx.client.alpn = None
        ctx.server.address = ("example.com", 443)
        ctx.client.transport_protocol = "udp"
        ctx.client.proxy_mode.scheme = "http3"
        ctx.layers = [
            layers.modes.ReverseProxy(ctx),
            layers.ServerQuicLayer(ctx),
        ]
        assert isinstance(nl._next_layer(ctx, b"notahandshakebutignore", b""), layers.ClientQuicLayer)
        decision = nl._next_layer(ctx, b"", b"")
        assert isinstance(decision, layers.HttpLayer)
        assert decision.mode is HTTPMode.transparent

    def test_next_layer_reverse_invalid_mode(self):
        nl = NextLayer()
        ctx = MagicMock()
        ctx.client.alpn = None
        ctx.server.address = ("example.com", 443)
        ctx.client.transport_protocol = "udp"
        ctx.client.proxy_mode.scheme = "invalidscheme"
        ctx.layers = [layers.modes.ReverseProxy(ctx)]
        with pytest.raises(AssertionError, match="invalidscheme"):
            nl._next_layer(ctx, b"", b"")

    def test_next_layer_reverse_dtls_mode(self):
        nl = NextLayer()
        ctx = MagicMock()
        ctx.client.alpn = None
        ctx.server.address = ("example.com", 443)
        ctx.client.transport_protocol = "udp"
        ctx.client.proxy_mode.scheme = "dtls"
        ctx.layers = [layers.modes.ReverseProxy(ctx), layers.ServerTLSLayer(ctx)]
        assert isinstance(nl._next_layer(ctx, b"", b""), layers.UDPLayer)
        ctx.layers = [layers.modes.ReverseProxy(ctx), layers.ServerTLSLayer(ctx), layers.ClientTLSLayer(ctx)]
        assert isinstance(nl._next_layer(ctx, b"", b""), layers.UDPLayer)

    def test_next_layer_reverse_udp_mode(self):
        nl = NextLayer()
        ctx = MagicMock()
        ctx.client.alpn = None
        ctx.server.address = ("example.com", 443)
        ctx.client.transport_protocol = "udp"
        ctx.client.proxy_mode.scheme = "udp"
        ctx.layers = [layers.modes.ReverseProxy(ctx)]
        assert isinstance(nl._next_layer(ctx, b"", b""), layers.UDPLayer)
        ctx.layers = [layers.modes.ReverseProxy(ctx), layers.ClientTLSLayer(ctx)]
        assert isinstance(nl._next_layer(ctx, b"", b""), layers.UDPLayer)

    def test_next_layer_reverse_dns_mode(self):
        nl = NextLayer()
        ctx = MagicMock()
        ctx.client.alpn = None
        ctx.server.address = ("example.com", 443)
        ctx.client.transport_protocol = "udp"
        ctx.client.proxy_mode.scheme = "dns"
        ctx.layers = [layers.modes.ReverseProxy(ctx)]
        assert isinstance(nl._next_layer(ctx, b"", b""), layers.DNSLayer)
        ctx.layers = [layers.modes.ReverseProxy(ctx), layers.ClientTLSLayer(ctx)]
        assert isinstance(nl._next_layer(ctx, b"", b""), layers.DNSLayer)

    def test_next_layer_invalid_proto(self):
        nl = NextLayer()
        ctx = MagicMock()
        ctx.client.transport_protocol = "invalid"
        with taddons.context(nl):
            with pytest.raises(AssertionError):
                nl._next_layer(ctx, b"", b"")
