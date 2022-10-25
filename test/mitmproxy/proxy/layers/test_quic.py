import ssl
import time
from aioquic.buffer import Buffer as QuicBuffer
from aioquic.quic import events as quic_events
from aioquic.quic.configuration import QuicConfiguration
from aioquic.quic.connection import QuicConnection, pull_quic_header
from typing import Optional
from unittest.mock import MagicMock
import pytest
from mitmproxy import connection, options
from mitmproxy.addons.proxyserver import Proxyserver
from mitmproxy.proxy import commands, context, events, layer, tunnel
from mitmproxy.proxy import layers
from mitmproxy.proxy.layers import quic, tls
from mitmproxy.utils import data
from test.mitmproxy.proxy import tutils

from mitmproxy.tcp import TCPFlow


tlsdata = data.Data(__name__)


@pytest.fixture
def tctx() -> context.Context:
    opts = options.Options()
    Proxyserver().load(opts)
    return context.Context(
        connection.Client(("client", 1234), ("127.0.0.1", 8080), 1605699329), opts
    )


def test_error_code_to_str():
    assert quic.error_code_to_str(0x6) == "FINAL_SIZE_ERROR"
    assert quic.error_code_to_str(0x104) == "H3_CLOSED_CRITICAL_STREAM"
    assert quic.error_code_to_str(0xdead) == f"unknown error (0xdead)"


def test_is_success_error_code():
    assert quic.is_success_error_code(0x0)
    assert not quic.is_success_error_code(0x6)
    assert quic.is_success_error_code(0x100)
    assert not quic.is_success_error_code(0x104)
    assert not quic.is_success_error_code(0xdead)


client_hello = bytes.fromhex(
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


def test_parse_client_hello():
    assert quic.quic_parse_client_hello(client_hello).sni == "example.com"
    with pytest.raises(ValueError):
        quic.quic_parse_client_hello(
            client_hello[:183] + b"\x00\x00\x00\x00\x00\x00\x00\x00\x00"
        )


@pytest.mark.parametrize("value", ["s1 s2\n", "s1 s2"])
def test_secrets_logger(value: str):
    logger = MagicMock()
    quic_logger = quic.QuicSecretsLogger(logger)
    assert quic_logger.write(value) == 6
    quic_logger.flush()
    logger.assert_called_once()
    logger.assert_called_once_with(None, b"s1 s2")


def test_quic_stream_layer_ignored(tctx: context.Context):
    quic_layer = quic.QuicStreamLayer(tctx, True, 1)
    assert isinstance(quic_layer.child_layer, layers.TCPLayer)
    assert not quic_layer.child_layer.flow
    quic_layer.child_layer.flow = TCPFlow(MagicMock(), MagicMock())
    quic_layer.refresh_metadata()
    assert quic_layer.child_layer.flow.metadata["quic_is_unidirectional"] is False
    assert quic_layer.child_layer.flow.metadata["quic_initiator"] == "server"
    assert quic_layer.child_layer.flow.metadata["quic_stream_id_client"] == 1
    assert quic_layer.child_layer.flow.metadata["quic_stream_id_server"] is None
    assert quic_layer.stream_id(True) == 1
    assert quic_layer.stream_id(False) is None


def test_quic_stream_layer(tctx: context.Context):
    quic_layer = quic.QuicStreamLayer(tctx, False, 2)
    assert isinstance(quic_layer.child_layer, layer.NextLayer)
    tunnel_layer = tunnel.TunnelLayer(tctx, MagicMock(), MagicMock())
    quic_layer.child_layer.layer = tunnel_layer
    tcp_layer = layers.TCPLayer(tctx)
    tunnel_layer.child_layer = tcp_layer
    quic_layer.open_server_stream(3)
    assert tcp_layer.flow.metadata["quic_is_unidirectional"] is True
    assert tcp_layer.flow.metadata["quic_initiator"] == "client"
    assert tcp_layer.flow.metadata["quic_stream_id_client"] == 2
    assert tcp_layer.flow.metadata["quic_stream_id_server"] == 3
    assert quic_layer.stream_id(True) == 2
    assert quic_layer.stream_id(False) == 3


@pytest.mark.parametrize("ignore", [True, False])
def test_raw_quic_layer_error(tctx: context.Context, ignore: bool):
    quic_layer = quic.RawQuicLayer(tctx, ignore=ignore)
    assert (
        tutils.Playbook(quic_layer)
        << commands.OpenConnection(tctx.server)
        >> tutils.reply("failed to open")
        << commands.CloseConnection(tctx.client)
    )
    assert quic_layer._handle_event == quic_layer.done


def test_raw_quic_layer_ignored(tctx: context.Context):
    quic_layer = quic.RawQuicLayer(tctx, ignore=True)
    assert (
        tutils.Playbook(quic_layer)
        << commands.OpenConnection(tctx.server)
        >> tutils.reply(None)
        >> events.DataReceived(tctx.client, b"msg1")
        << commands.SendData(tctx.server, b"msg1")
        >> events.DataReceived(tctx.server, b"msg2")
        << commands.SendData(tctx.client, b"msg2")
        >> quic.QuicStreamDataReceived(tctx.client, 0, b"msg3", end_stream=False)
        << quic.SendQuicStreamData(tctx.server, 0, b"msg3", end_stream=False)
        >> quic.QuicStreamDataReceived(tctx.client, 6, b"msg4", end_stream=False)
        << quic.SendQuicStreamData(tctx.server, 2, b"msg4", end_stream=False)
        >> quic.QuicStreamDataReceived(tctx.server, 9, b"msg5", end_stream=False)
        << quic.SendQuicStreamData(tctx.client, 1, b"msg5", end_stream=False)
        >> quic.QuicStreamDataReceived(tctx.client, 0, b"", end_stream=True)
        << quic.SendQuicStreamData(tctx.server, 0, b"", end_stream=True)
        >> quic.QuicConnectionClosed(tctx.client, 42, None, "closed")
        << quic.CloseQuicConnection(tctx.server, 42, None, "closed")
        >> quic.QuicConnectionClosed(tctx.server, 42, None, "closed")
        << None
    )
    assert quic_layer._handle_event == quic_layer.done


class SSLTest:
    """Helper container for Python's builtin SSL object."""

    def __init__(
        self,
        server_side: bool = False,
        alpn: Optional[list[str]] = None,
        sni: Optional[bytes] = b"example.mitmproxy.org",
    ):
        self.ctx = QuicConfiguration(
            is_client=not server_side,
            max_datagram_frame_size=65536,
        )

        self.ctx.verify_mode = ssl.CERT_OPTIONAL
        self.ctx.load_verify_locations(
            cafile=tlsdata.path("../../net/data/verificationcerts/trusted-root.crt"),
        )

        if alpn:
            self.ctx.alpn_protocols = alpn
        if server_side:
            if sni == b"192.0.2.42":
                filename = "trusted-leaf-ip"
            else:
                filename = "trusted-leaf"
            self.ctx.load_cert_chain(
                certfile=tlsdata.path(
                    f"../../net/data/verificationcerts/{filename}.crt"
                ),
                keyfile=tlsdata.path(
                    f"../../net/data/verificationcerts/{filename}.key"
                ),
            )

        self.ctx.server_name = None if server_side else sni

        self.quic = None if server_side else QuicConnection(configuration=self.ctx)

    def write(self, buf: bytes) -> int:
        if self.quic is None:
            quic_buf = QuicBuffer(data=buf)
            header = pull_quic_header(quic_buf, host_cid_length=8)
            self.quic = QuicConnection(
                configuration=self.ctx,
                original_destination_connection_id=header.destination_cid,
            )
        self.quic.receive_datagram(buf, ("0.0.0.0", 0), time.time())

    def read(self) -> bytes:
        buf = b""
        has_data = False
        for datagram, addr in self.quic.datagrams_to_send(time.time()):
            assert addr == ("0.0.0.0", 0)
            buf += datagram
            has_data = True
        if not has_data:
            raise AssertionError("no datagrams to send")
        return buf

    def handshake_completed(self) -> bool:
        while event := self.quic.next_event():
            if isinstance(event, quic_events.HandshakeCompleted):
                return True
        else:
            return False


def _test_echo(
    playbook: tutils.Playbook, tssl: SSLTest, conn: connection.Connection
) -> None:
    tssl.quic.send_datagram_frame(b"Hello World")
    data = tutils.Placeholder(bytes)
    assert (
        playbook
        >> events.DataReceived(conn, tssl.read())
        << commands.SendData(conn, data)
    )
    tssl.write(data())
    while event := tssl.quic.next_event():
        if isinstance(event, quic_events.DatagramFrameReceived):
            assert event.data == b"hello world"
    else:
        raise AssertionError()


class TlsEchoLayer(tutils.EchoLayer):
    err: Optional[str] = None

    def _handle_event(self, event: events.Event) -> layer.CommandGenerator[None]:
        if isinstance(event, events.DataReceived) and event.data == b"open-connection":
            err = yield commands.OpenConnection(self.context.server)
            if err:
                yield commands.SendData(
                    event.connection, f"open-connection failed: {err}".encode()
                )
        else:
            yield from super()._handle_event(event)


def finish_handshake(
    playbook: tutils.Playbook, conn: connection.Connection, tssl: SSLTest
):
    data = tutils.Placeholder(bytes)
    tls_hook_data = tutils.Placeholder(tls.TlsData)
    if isinstance(conn, connection.Client):
        established_hook = tls.TlsEstablishedClientHook(tls_hook_data)
    else:
        established_hook = tls.TlsEstablishedServerHook(tls_hook_data)
    assert (
        playbook
        >> events.DataReceived(conn, tssl.read())
        << established_hook
        >> tutils.reply()
        << commands.SendData(conn, data)
        << layer.NextLayerHook(tutils.Placeholder())
        >> tutils.reply_next_layer(TlsEchoLayer)
    )
    assert tls_hook_data().conn.error is None
    tssl.write(data())


def reply_tls_start_server(*args, **kwargs) -> tutils.reply:
    """
    Helper function to simplify the syntax for quic_start_server hooks.
    """

    def make_server_conn(tls_start: quic.QuicTlsData) -> None:
        # ssl_context = SSL.Context(Method.TLS_METHOD)
        # ssl_context.set_min_proto_version(SSL.TLS1_3_VERSION)
        tls_start.settings = quic.QuicTlsSettings(
            ca_file=tlsdata.path("../../net/data/verificationcerts/trusted-root.crt"),
            verify_mode=ssl.CERT_REQUIRED,
        )

    return tutils.reply(*args, side_effect=make_server_conn, **kwargs)


class TestServerTLS:
    def test_repr(self, tctx: context.Context):
        assert repr(quic.ServerQuicLayer(tctx))

    def test_not_connected(self, tctx: context.Context):
        """Test that we don't do anything if no server connection exists."""
        layer = quic.ServerQuicLayer(tctx)
        layer.child_layer = TlsEchoLayer(tctx)

        assert (
            tutils.Playbook(layer)
            >> events.DataReceived(tctx.client, b"Hello World")
            << commands.SendData(tctx.client, b"hello world")
        )

    def test_simple(self, tctx: context.Context):
        playbook = tutils.Playbook(quic.ServerQuicLayer(tctx))
        tctx.server.address = ("example.mitmproxy.org", 443)
        tctx.server.state = connection.ConnectionState.OPEN
        tctx.server.sni = "example.mitmproxy.org"

        tssl = SSLTest(server_side=True)

        # send ClientHello, receive ClientHello
        data = tutils.Placeholder(bytes)
        assert (
            playbook
            << quic.QuicStartServerHook(tutils.Placeholder())
            >> reply_tls_start_server()
            << commands.SendData(tctx.server, data)
            << commands.RequestWakeup(tutils.Placeholder())
        )
        tssl.write(data())
        assert not tssl.handshake_completed()

        # finish handshake (mitmproxy)
        finish_handshake(playbook, tctx.server, tssl)

        # finish handshake (locally)
        assert tssl.handshake_completed()
        playbook >> events.DataReceived(tctx.server, tssl.read())
        playbook << None
        assert playbook

        assert tctx.server.tls_established

        # Echo
        assert (
            playbook
            >> events.DataReceived(tctx.client, b"foo")
            << commands.SendData(tctx.client, b"foo")
        )

