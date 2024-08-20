from __future__ import annotations

import dataclasses
import logging
from collections.abc import Sequence
from dataclasses import dataclass
from functools import partial
from unittest.mock import MagicMock

import pytest

from mitmproxy.addons.next_layer import NeedsMoreData
from mitmproxy.addons.next_layer import NextLayer
from mitmproxy.addons.next_layer import stack_match
from mitmproxy.connection import Address
from mitmproxy.connection import Client
from mitmproxy.connection import TransportProtocol
from mitmproxy.proxy.context import Context
from mitmproxy.proxy.layer import Layer
from mitmproxy.proxy.layers import ClientQuicLayer
from mitmproxy.proxy.layers import ClientTLSLayer
from mitmproxy.proxy.layers import DNSLayer
from mitmproxy.proxy.layers import HttpLayer
from mitmproxy.proxy.layers import modes
from mitmproxy.proxy.layers import QuicStreamLayer
from mitmproxy.proxy.layers import RawQuicLayer
from mitmproxy.proxy.layers import ServerQuicLayer
from mitmproxy.proxy.layers import ServerTLSLayer
from mitmproxy.proxy.layers import TCPLayer
from mitmproxy.proxy.layers import UDPLayer
from mitmproxy.proxy.layers.http import HTTPMode
from mitmproxy.proxy.layers.http import HttpStream
from mitmproxy.proxy.layers.tls import HTTP1_ALPNS
from mitmproxy.proxy.layers.tls import HTTP3_ALPN
from mitmproxy.proxy.mode_specs import ProxyMode
from mitmproxy.test import taddons

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
    "16fefd00000000000000000085"  # record layer
    "010000790000000000000079"  # handshake layer
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

dns_query = bytes.fromhex("002a01000001000000000000076578616d706c6503636f6d0000010001")

# Custom protocol with just base64-encoded messages
# https://github.com/mitmproxy/mitmproxy/pull/7087
custom_base64_proto = b"AAAAAAAAAAAAAAAAAAAAAA=="

http_get = b"GET / HTTP/1.1\r\nHost: example.com\r\n\r\n"
http_get_absolute = b"GET http://example.com/ HTTP/1.1\r\n\r\n"

http_connect = b"CONNECT example.com:443 HTTP/1.1\r\nHost: example.com:443\r\n\r\n"


class TestNextLayer:
    @pytest.mark.parametrize(
        "ignore, allow, transport_protocol, server_address, data_client, result",
        [
            # ignore
            pytest.param(
                [], [], "tcp", "example.com", b"", False, id="nothing ignored"
            ),
            pytest.param(
                ["example.com"], [], "tcp", "example.com", b"", True, id="address"
            ),
            pytest.param(
                ["192.0.2.1"], [], "tcp", "example.com", b"", True, id="ip address"
            ),
            pytest.param(
                ["2001:db8::1"],
                [],
                "tcp",
                "ipv6.example.com",
                b"",
                True,
                id="ipv6 address",
            ),
            pytest.param(
                ["example.com:443"],
                [],
                "tcp",
                "example.com",
                b"",
                True,
                id="port matches",
            ),
            pytest.param(
                ["example.com:123"],
                [],
                "tcp",
                "example.com",
                b"",
                False,
                id="port does not match",
            ),
            pytest.param(
                ["example.com"],
                [],
                "tcp",
                "192.0.2.1",
                http_get,
                True,
                id="http host header",
            ),
            pytest.param(
                ["example.com"],
                [],
                "tcp",
                "192.0.2.1",
                http_get.replace(b"Host", b"X-Host"),
                False,
                id="http host header missing",
            ),
            pytest.param(
                ["example.com"],
                [],
                "tcp",
                "192.0.2.1",
                http_get.split(b"\r\n", 1)[0],
                NeedsMoreData,
                id="incomplete http host header",
            ),
            pytest.param(
                ["example.com"],
                [],
                "tcp",
                "com",
                b"",
                False,
                id="partial address match",
            ),
            pytest.param(
                ["example.com"],
                [],
                "tcp",
                None,
                b"",
                False,
                id="no destination info",
            ),
            pytest.param(
                ["example.com"],
                [],
                "tcp",
                None,
                client_hello_no_extensions,
                False,
                id="no sni",
            ),
            pytest.param(
                ["example.com"],
                [],
                "tcp",
                "192.0.2.1",
                client_hello_with_extensions,
                True,
                id="sni",
            ),
            pytest.param(
                ["example.com"],
                [],
                "tcp",
                "192.0.2.1",
                client_hello_with_extensions[:-5],
                NeedsMoreData,
                id="incomplete client hello",
            ),
            pytest.param(
                ["example.com"],
                [],
                "tcp",
                "192.0.2.1",
                client_hello_no_extensions[:9] + b"\x00" * 200,
                False,
                id="invalid client hello",
            ),
            pytest.param(
                ["example.com"],
                [],
                "tcp",
                "decoy",
                client_hello_with_extensions,
                True,
                id="sni mismatch",
            ),
            pytest.param(
                ["example.com"],
                [],
                "udp",
                "192.0.2.1",
                dtls_client_hello_with_extensions,
                True,
                id="dtls sni",
            ),
            pytest.param(
                ["example.com"],
                [],
                "udp",
                "192.0.2.1",
                dtls_client_hello_with_extensions[:-5],
                NeedsMoreData,
                id="incomplete dtls client hello",
            ),
            pytest.param(
                ["example.com"],
                [],
                "udp",
                "192.0.2.1",
                dtls_client_hello_with_extensions[:9] + b"\x00" * 200,
                False,
                id="invalid dtls client hello",
            ),
            pytest.param(
                ["example.com"],
                [],
                "udp",
                "192.0.2.1",
                quic_client_hello,
                True,
                id="quic sni",
            ),
            # allow
            pytest.param(
                [],
                ["example.com"],
                "tcp",
                "example.com",
                b"",
                False,
                id="allow: allow",
            ),
            pytest.param(
                [],
                ["example.com"],
                "tcp",
                "example.org",
                b"",
                True,
                id="allow: ignore",
            ),
            pytest.param(
                [],
                ["example.com"],
                "tcp",
                "192.0.2.1",
                client_hello_with_extensions,
                False,
                id="allow: sni",
            ),
            pytest.param(
                [],
                ["existing-sni.example"],
                "tcp",
                "192.0.2.1",
                b"",
                False,
                id="allow: sni from parent layer",
            ),
            pytest.param(
                [],
                ["example.com"],
                "tcp",
                "decoy",
                client_hello_with_extensions,
                False,
                id="allow: sni mismatch",
            ),
            # allow with ignore
            pytest.param(
                ["binary.example.com"],
                ["example.com"],
                "tcp",
                "example.com",
                b"",
                False,
                id="allow+ignore: allowed and not ignored",
            ),
            pytest.param(
                ["binary.example.com"],
                ["example.com"],
                "tcp",
                "binary.example.org",
                b"",
                True,
                id="allow+ignore: allowed but ignored",
            ),
        ],
    )
    def test_ignore_connection(
        self,
        ignore: list[str],
        allow: list[str],
        transport_protocol: TransportProtocol,
        server_address: str,
        data_client: bytes,
        result: bool | type[NeedsMoreData],
    ):
        nl = NextLayer()
        with taddons.context(nl) as tctx:
            if ignore:
                tctx.configure(nl, ignore_hosts=ignore)
            if allow:
                tctx.configure(nl, allow_hosts=allow)
            ctx = Context(
                Client(
                    peername=("192.168.0.42", 51234),
                    sockname=("0.0.0.0", 8080),
                    sni="existing-sni.example",
                ),
                tctx.options,
            )
            ctx.client.transport_protocol = transport_protocol
            if server_address:
                ctx.server.address = (server_address, 443)
                ctx.server.peername = (
                    ("2001:db8::1", 443, 0, 0)
                    if server_address.startswith("ipv6")
                    else ("192.0.2.1", 443)
                )
            if result is NeedsMoreData:
                with pytest.raises(NeedsMoreData):
                    nl._ignore_connection(ctx, data_client, b"")
            else:
                assert nl._ignore_connection(ctx, data_client, b"") is result

    def test_next_layer(self, monkeypatch, caplog):
        caplog.set_level(logging.INFO)
        nl = NextLayer()

        with taddons.context(nl) as tctx:
            m = MagicMock()
            m.context = Context(
                Client(peername=("192.168.0.42", 51234), sockname=("0.0.0.0", 8080)),
                tctx.options,
            )
            m.context.layers = [modes.TransparentProxy(m.context)]
            m.context.server.address = ("example.com", 42)
            tctx.configure(nl, ignore_hosts=["example.com"])

            m.layer = preexisting = object()
            nl.next_layer(m)
            assert m.layer is preexisting

            m.layer = None
            monkeypatch.setattr(m, "data_client", lambda: http_get)
            nl.next_layer(m)
            assert m.layer

            m.layer = None
            monkeypatch.setattr(
                m, "data_client", lambda: client_hello_with_extensions[:-5]
            )
            nl.next_layer(m)
            assert not m.layer
            assert "Deferring layer decision" in caplog.text


@dataclass
class TConf:
    before: list[type[Layer]]
    after: list[type[Layer]]
    proxy_mode: str = "regular"
    transport_protocol: TransportProtocol = "tcp"
    data_client: bytes = b""
    data_server: bytes = b""
    ignore_hosts: Sequence[str] = ()
    tcp_hosts: Sequence[str] = ()
    udp_hosts: Sequence[str] = ()
    ignore_conn: bool = False
    server_address: Address | None = None
    alpn: bytes | None = None


explicit_proxy_configs = [
    pytest.param(
        TConf(
            before=[modes.HttpProxy],
            after=[modes.HttpProxy, HttpLayer],
            data_client=http_connect,
        ),
        id=f"explicit proxy: regular http connect",
    ),
    pytest.param(
        TConf(
            before=[modes.HttpProxy],
            after=[modes.HttpProxy, HttpLayer],
            ignore_hosts=[".+"],
            data_client=http_connect,
        ),
        id=f"explicit proxy: regular http connect disregards ignore_hosts",
    ),
    pytest.param(
        TConf(
            before=[modes.HttpProxy],
            after=[modes.HttpProxy, HttpLayer],
            ignore_hosts=[".+"],
            data_client=http_get_absolute,
        ),
        id=f"explicit proxy: HTTP over regular proxy disregards ignore_hosts",
    ),
    pytest.param(
        TConf(
            before=[modes.HttpProxy],
            after=[modes.HttpProxy, ClientTLSLayer, HttpLayer],
            data_client=client_hello_no_extensions,
        ),
        id=f"explicit proxy: secure web proxy",
    ),
    pytest.param(
        TConf(
            before=[modes.HttpUpstreamProxy],
            after=[modes.HttpUpstreamProxy, HttpLayer],
        ),
        id=f"explicit proxy: upstream proxy",
    ),
    pytest.param(
        TConf(
            before=[modes.HttpUpstreamProxy],
            after=[modes.HttpUpstreamProxy, ClientQuicLayer, HttpLayer],
            transport_protocol="udp",
        ),
        id=f"explicit proxy: experimental http3",
    ),
    pytest.param(
        TConf(
            before=[
                modes.HttpProxy,
                partial(HttpLayer, mode=HTTPMode.regular),
                partial(HttpStream, stream_id=1),
            ],
            after=[modes.HttpProxy, HttpLayer, HttpStream, HttpLayer],
            data_client=b"GET / HTTP/1.1\r\n",
        ),
        id=f"explicit proxy: HTTP over regular proxy",
    ),
    pytest.param(
        TConf(
            before=[
                modes.HttpProxy,
                partial(HttpLayer, mode=HTTPMode.regular),
                partial(HttpStream, stream_id=1),
            ],
            after=[
                modes.HttpProxy,
                HttpLayer,
                HttpStream,
                ServerTLSLayer,
                ClientTLSLayer,
            ],
            data_client=client_hello_with_extensions,
        ),
        id=f"explicit proxy: TLS over regular proxy",
    ),
    pytest.param(
        TConf(
            before=[
                modes.HttpProxy,
                partial(HttpLayer, mode=HTTPMode.regular),
                partial(HttpStream, stream_id=1),
                ServerTLSLayer,
                ClientTLSLayer,
            ],
            after=[
                modes.HttpProxy,
                HttpLayer,
                HttpStream,
                ServerTLSLayer,
                ClientTLSLayer,
                HttpLayer,
            ],
            data_client=b"GET / HTTP/1.1\r\n",
        ),
        id=f"explicit proxy: HTTPS over regular proxy",
    ),
    pytest.param(
        TConf(
            before=[
                modes.HttpProxy,
                partial(HttpLayer, mode=HTTPMode.regular),
                partial(HttpStream, stream_id=1),
            ],
            after=[modes.HttpProxy, HttpLayer, HttpStream, TCPLayer],
            data_client=b"\xff",
        ),
        id=f"explicit proxy: TCP over regular proxy",
    ),
]

reverse_proxy_configs = []
for proto_plain, proto_enc, app_layer in [
    ("udp", "dtls", UDPLayer),
    ("tcp", "tls", TCPLayer),
    ("http", "https", HttpLayer),
]:
    if proto_plain == "udp":
        data_client = dtls_client_hello_with_extensions
    else:
        data_client = client_hello_with_extensions

    reverse_proxy_configs.extend(
        [
            pytest.param(
                TConf(
                    before=[modes.ReverseProxy],
                    after=[modes.ReverseProxy, app_layer],
                    proxy_mode=f"reverse:{proto_plain}://example.com:42",
                ),
                id=f"reverse proxy: {proto_plain} -> {proto_plain}",
            ),
            pytest.param(
                TConf(
                    before=[modes.ReverseProxy],
                    after=[
                        modes.ReverseProxy,
                        ServerTLSLayer,
                        ClientTLSLayer,
                        app_layer,
                    ],
                    proxy_mode=f"reverse:{proto_enc}://example.com:42",
                    data_client=data_client,
                ),
                id=f"reverse proxy: {proto_enc} -> {proto_enc}",
            ),
            pytest.param(
                TConf(
                    before=[modes.ReverseProxy],
                    after=[modes.ReverseProxy, ClientTLSLayer, app_layer],
                    proxy_mode=f"reverse:{proto_plain}://example.com:42",
                    data_client=data_client,
                ),
                id=f"reverse proxy: {proto_enc} -> {proto_plain}",
            ),
            pytest.param(
                TConf(
                    before=[modes.ReverseProxy],
                    after=[modes.ReverseProxy, ServerTLSLayer, app_layer],
                    proxy_mode=f"reverse:{proto_enc}://example.com:42",
                ),
                id=f"reverse proxy: {proto_plain} -> {proto_enc}",
            ),
        ]
    )

reverse_proxy_configs.extend(
    [
        pytest.param(
            TConf(
                before=[modes.ReverseProxy],
                after=[modes.ReverseProxy, DNSLayer],
                proxy_mode="reverse:dns://example.com:53",
            ),
            id="reverse proxy: dns",
        ),
        pytest.param(
            http3 := TConf(
                before=[modes.ReverseProxy],
                after=[modes.ReverseProxy, ServerQuicLayer, ClientQuicLayer, HttpLayer],
                proxy_mode="reverse:http3://example.com",
            ),
            id="reverse proxy: http3",
        ),
        pytest.param(
            dataclasses.replace(
                http3,
                proxy_mode="reverse:https://example.com",
                transport_protocol="udp",
            ),
            id="reverse proxy: http3 in https mode",
        ),
        pytest.param(
            TConf(
                before=[modes.ReverseProxy],
                after=[
                    modes.ReverseProxy,
                    ServerQuicLayer,
                    ClientQuicLayer,
                    RawQuicLayer,
                ],
                proxy_mode="reverse:quic://example.com",
            ),
            id="reverse proxy: quic",
        ),
        pytest.param(
            TConf(
                before=[
                    modes.ReverseProxy,
                    ServerQuicLayer,
                    ClientQuicLayer,
                    RawQuicLayer,
                    lambda ctx: QuicStreamLayer(ctx, False, 0),
                ],
                after=[
                    modes.ReverseProxy,
                    ServerQuicLayer,
                    ClientQuicLayer,
                    RawQuicLayer,
                    QuicStreamLayer,
                    TCPLayer,
                ],
                proxy_mode="reverse:quic://example.com",
                alpn=HTTP3_ALPN,
            ),
            id="reverse proxy: quic",
        ),
        pytest.param(
            TConf(
                before=[modes.ReverseProxy],
                after=[modes.ReverseProxy, TCPLayer],
                proxy_mode=f"reverse:http://example.com",
                ignore_hosts=["example.com"],
                server_address=("example.com", 80),
                data_client=http_get,
                ignore_conn=True,
            ),
            id="reverse proxy: ignore_hosts",
        ),
    ]
)

transparent_proxy_configs = [
    pytest.param(
        TConf(
            before=[modes.TransparentProxy],
            after=[modes.TransparentProxy, ServerTLSLayer, ClientTLSLayer],
            data_client=client_hello_no_extensions,
        ),
        id=f"transparent proxy: tls",
    ),
    pytest.param(
        TConf(
            before=[modes.TransparentProxy],
            after=[modes.TransparentProxy, ServerTLSLayer, ClientTLSLayer],
            data_client=dtls_client_hello_with_extensions,
            transport_protocol="udp",
        ),
        id=f"transparent proxy: dtls",
    ),
    pytest.param(
        TConf(
            before=[modes.TransparentProxy],
            after=[modes.TransparentProxy, ServerQuicLayer, ClientQuicLayer],
            data_client=quic_client_hello,
            transport_protocol="udp",
        ),
        id="transparent proxy: quic",
    ),
    pytest.param(
        TConf(
            before=[modes.TransparentProxy],
            after=[modes.TransparentProxy, TCPLayer],
            data_server=b"220 service ready",
        ),
        id="transparent proxy: raw tcp",
    ),
    pytest.param(
        http := TConf(
            before=[modes.TransparentProxy],
            after=[modes.TransparentProxy, HttpLayer],
            server_address=("192.0.2.1", 80),
            data_client=http_get,
        ),
        id="transparent proxy: http",
    ),
    pytest.param(
        TConf(
            before=[modes.TransparentProxy, ServerTLSLayer, ClientTLSLayer],
            after=[modes.TransparentProxy, ServerTLSLayer, ClientTLSLayer, HttpLayer],
            data_client=b"GO /method-too-short-for-heuristic HTTP/1.1\r\n",
            alpn=HTTP1_ALPNS[0],
        ),
        id=f"transparent proxy: http via ALPN",
    ),
    pytest.param(
        TConf(
            before=[modes.TransparentProxy],
            after=[modes.TransparentProxy, TCPLayer],
            server_address=("192.0.2.1", 23),
            data_client=b"SSH-2.0-OpenSSH_9.7",
        ),
        id="transparent proxy: ssh",
    ),
    pytest.param(
        dataclasses.replace(
            http,
            tcp_hosts=["192.0.2.1"],
            after=[modes.TransparentProxy, TCPLayer],
        ),
        id="transparent proxy: tcp_hosts",
    ),
    pytest.param(
        dataclasses.replace(
            http,
            ignore_hosts=["192.0.2.1"],
            after=[modes.TransparentProxy, TCPLayer],
            ignore_conn=True,
        ),
        id="transparent proxy: ignore_hosts",
    ),
    pytest.param(
        TConf(
            before=[modes.TransparentProxy],
            after=[modes.TransparentProxy, TCPLayer],
            data_client=custom_base64_proto,
        ),
        id="transparent proxy: full alpha tcp",
    ),
    pytest.param(
        udp := TConf(
            before=[modes.TransparentProxy],
            after=[modes.TransparentProxy, UDPLayer],
            server_address=("192.0.2.1", 553),
            transport_protocol="udp",
            data_client=b"\xff",
        ),
        id="transparent proxy: raw udp",
    ),
    pytest.param(
        dns := dataclasses.replace(
            udp,
            after=[modes.TransparentProxy, DNSLayer],
            data_client=dns_query,
            server_address=("192.0.2.1", 53),
        ),
        id="transparent proxy: dns over udp",
    ),
    pytest.param(
        dataclasses.replace(
            dns,
            transport_protocol="tcp",
        ),
        id="transparent proxy: dns over tcp",
    ),
    pytest.param(
        dataclasses.replace(
            udp,
            udp_hosts=["192.0.2.1"],
            after=[modes.TransparentProxy, UDPLayer],
        ),
        id="transparent proxy: udp_hosts",
    ),
    pytest.param(
        TConf(
            before=[modes.TransparentProxy],
            after=[modes.TransparentProxy, DNSLayer],
            proxy_mode="wireguard",
            server_address=("10.0.0.53", 53),
            ignore_hosts=[".+"],
            transport_protocol="udp",
            data_client=dns_query,
        ),
        id="wireguard proxy: dns should not be ignored",
    ),
]


@pytest.mark.parametrize(
    "test_conf",
    [
        *explicit_proxy_configs,
        *reverse_proxy_configs,
        *transparent_proxy_configs,
    ],
)
def test_next_layer(
    test_conf: TConf,
):
    nl = NextLayer()
    with taddons.context(nl) as tctx:
        tctx.configure(
            nl,
            ignore_hosts=test_conf.ignore_hosts,
            tcp_hosts=test_conf.tcp_hosts,
            udp_hosts=test_conf.udp_hosts,
        )

        ctx = Context(
            Client(
                peername=("192.168.0.42", 51234),
                sockname=("0.0.0.0", 8080),
                alpn=test_conf.alpn,
            ),
            tctx.options,
        )
        ctx.server.address = test_conf.server_address
        ctx.client.transport_protocol = test_conf.transport_protocol
        ctx.client.proxy_mode = ProxyMode.parse(test_conf.proxy_mode)
        ctx.layers = [x(ctx) for x in test_conf.before]
        nl._next_layer(
            ctx,
            data_client=test_conf.data_client,
            data_server=test_conf.data_server,
        )
        assert stack_match(ctx, test_conf.after), f"Unexpected stack: {ctx.layers}"

        last_layer = ctx.layers[-1]
        if isinstance(last_layer, (UDPLayer, TCPLayer)):
            assert bool(last_layer.flow) ^ test_conf.ignore_conn
