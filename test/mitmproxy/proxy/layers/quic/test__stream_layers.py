import ssl
import time
from logging import DEBUG
from logging import ERROR
from logging import WARNING
from typing import Literal
from typing import TypeVar
from unittest.mock import MagicMock

import pytest
from aioquic.buffer import Buffer as QuicBuffer
from aioquic.quic import events as quic_events
from aioquic.quic.configuration import QuicConfiguration
from aioquic.quic.connection import pull_quic_header
from aioquic.quic.connection import QuicConnection

from mitmproxy import connection
from mitmproxy.proxy import commands
from mitmproxy.proxy import context
from mitmproxy.proxy import events
from mitmproxy.proxy import layer
from mitmproxy.proxy.layers import tls
from mitmproxy.proxy.layers.quic._commands import CloseQuicConnection
from mitmproxy.proxy.layers.quic._commands import QuicStreamCommand
from mitmproxy.proxy.layers.quic._commands import ResetQuicStream
from mitmproxy.proxy.layers.quic._commands import SendQuicStreamData
from mitmproxy.proxy.layers.quic._commands import StopSendingQuicStream
from mitmproxy.proxy.layers.quic._events import QuicConnectionClosed
from mitmproxy.proxy.layers.quic._events import QuicStreamDataReceived
from mitmproxy.proxy.layers.quic._events import QuicStreamReset
from mitmproxy.proxy.layers.quic._events import QuicStreamStopSending
from mitmproxy.proxy.layers.quic._hooks import QuicStartClientHook
from mitmproxy.proxy.layers.quic._hooks import QuicStartServerHook
from mitmproxy.proxy.layers.quic._hooks import QuicTlsData
from mitmproxy.proxy.layers.quic._hooks import QuicTlsSettings
from mitmproxy.proxy.layers.quic._stream_layers import ClientQuicLayer
from mitmproxy.proxy.layers.quic._stream_layers import error_code_to_str
from mitmproxy.proxy.layers.quic._stream_layers import is_success_error_code
from mitmproxy.proxy.layers.quic._stream_layers import QuicLayer
from mitmproxy.proxy.layers.quic._stream_layers import QuicSecretsLogger
from mitmproxy.proxy.layers.quic._stream_layers import ServerQuicLayer
from mitmproxy.proxy.layers.quic._stream_layers import tls_settings_to_configuration
from mitmproxy.utils import data
from test.mitmproxy.proxy import tutils

tdata = data.Data("test")


T = TypeVar("T", bound=layer.Layer)


class DummyLayer(layer.Layer):
    child_layer: layer.Layer | None

    def _handle_event(self, event: events.Event) -> layer.CommandGenerator[None]:
        assert self.child_layer
        return self.child_layer.handle_event(event)


class TlsEchoLayer(tutils.EchoLayer):
    err: str | None = None
    closed: QuicConnectionClosed | None = None

    def _handle_event(self, event: events.Event) -> layer.CommandGenerator[None]:
        if isinstance(event, events.DataReceived) and event.data == b"open-connection":
            err = yield commands.OpenConnection(self.context.server)
            if err:
                yield commands.SendData(
                    event.connection, f"open-connection failed: {err}".encode()
                )
        elif (
            isinstance(event, events.DataReceived) and event.data == b"close-connection"
        ):
            yield commands.CloseConnection(event.connection)
        elif (
            isinstance(event, events.DataReceived)
            and event.data == b"close-connection-error"
        ):
            yield CloseQuicConnection(event.connection, 123, None, "error")
        elif (
            isinstance(event, events.DataReceived) and event.data == b"invalid-command"
        ):

            class InvalidConnectionCommand(commands.ConnectionCommand):
                pass

            yield InvalidConnectionCommand(event.connection)
        elif (
            isinstance(event, events.DataReceived)
            and event.data == b"invalid-stream-command"
        ):

            class InvalidStreamCommand(QuicStreamCommand):
                pass

            yield InvalidStreamCommand(event.connection, 42)
        elif isinstance(event, QuicConnectionClosed):
            self.closed = event
        elif isinstance(event, QuicStreamDataReceived):
            yield SendQuicStreamData(
                event.connection, event.stream_id, event.data, event.end_stream
            )
        elif isinstance(event, QuicStreamReset):
            yield ResetQuicStream(event.connection, event.stream_id, event.error_code)
        elif isinstance(event, QuicStreamStopSending):
            yield StopSendingQuicStream(
                event.connection, event.stream_id, event.error_code
            )
        else:
            yield from super()._handle_event(event)


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


fragmented_client_hello1 = bytes.fromhex(
    "c20000000108d520c3803f5de4d3000044bcb607af28f41aef1616d37bdc7697d73d7963a2d622e7ccddfb4859"
    "f369d840f949a29bb19ad7264728eb31eada17a4e1ba666bba67868cf2c30ca4e1d41f67d392c296787a50615a"
    "1caf4282f9cc59c98816e1734b57ba4dedf02c225a3f57163bb77703299fafb46d09a4d281eb44f988edd28984"
    "04a7161cf7454d8e184f87ae9be1f3bd2c2ae04ba14233ec92960a75a4201bc114070ecfd4c10a4fb0c72749ee"
    "b5fa0e52b53dc0da6a485eb8bb467e7a1972c4e1c3a38622857b44eb94d653ee2f2e1fa3bf3f01cacd17b2668a"
    "8578e04da4181f3d6ad4031e4f7adec95d015d4f275505ae14fa03154b18c3b838143fac06cb2c8b395effa47c"
    "08923e352d1c4beff9e228760f5a80e6214485c7e53efd8d649492aafb3a9c9472335569c2d7971c86f319069e"
    "c6ccd13b0b8f517c51fc2e42dc5e7bc3434f306955cf1dc575ea9e18617699045b92b006599afd94abb25018ea"
    "f63cfcc247f76b728c4fc4e663dff64b90059d1d27f8ecd63bb548862b88bcd52e0711f222b15c022d214a2cc3"
    "93e537e32d149c67aa84692f1a204475a7acceaa0ab5f823ea90af601bdfb7f4036971e1c786fca7fa7e8ab042"
    "24307bcc3093886b54e4c9e6b7cb286d6259a8231ffae0f589f687f92232ac5384988631efb70dc85fc594bb3c"
    "1c0ceebc08b37d8989da0ae786e30d1278ffddbac47484346afd8439495aa1d392ce76f8ebc8d3d1870a0698ca"
    "b133cabbacae924013025e7bce5ac6aaf87684b6409a6a58e8bb294c249a5c7ca9b2961c57dc031485e3a000ec"
    "ea4e908cf9f33e86f0fd5d4ca5996b73c273dfda3fe68aa6a385984cb7fd2bf5f69d997580b407d48845215422"
    "c3c9fe52e7aa4b4e11c067db3e7c87c55f3b1400f796a4b873b666b7027c33138c1f310f65e20b53bcba019f1e"
    "08aee1a89430744c8bd2dd3a788410caa4356099b87cab2463da107a6919af38c159a258ff6693dd71f1941a52"
    "01d6a0b2fc52cfab6e0ba2c84c6231bc2a54fe1b6af1641e1168599ea03da913e537880f13128515085fd17b47"
    "fe202b82152d1c7df2e66788a2d0e0aab0e6375d368f8064e29912f32d4c509408a642a597bcf39c3e6fe31873"
    "e6173067cf3fc65702152e43a9d2cc7262e69550bd3c10e833c3c5ec48878b214426eca9cdc169f59cbc2c93dc"
    "94562e05d94761c9f76191b505097dca964d56b9889f904347f6b250f5a1f2bf3c9e9f4370a164a4185e0d83c0"
    "96e1799b8d950535cf96eec690fa765e9e74baea45f3157ba8c78158d365acc1a5abb358093cca6afcde287096"
    "ba74b4238789ede0947083facfc9bb3129361a283d72fe860c9666877fb263650410ae5af9fd48e9a2214f9f0a"
    "39f3b55edca84c836a745f8fc294d176b878fede1e375358d2e63bbbc0632752b19afda03e527b6e9deb32b0a8"
    "e617f5396312b7769ccd164e43ba1ada90d97005ab8e4eda57d3a953b5cf5fac9676fc64dd7163bdb6b17f6984"
    "f70070f2eadace62317215f240100db10283cd4b7c62f2ba1191c0feee9e6fc6026dcaec12ecb2329221130aac"
    "18f08b091f5292e51c0ca35cfefabf9b86d8478f7cc9f2983260e6cec537081684119a02d51e0895d9ee9294cf"
    "a6f695173fa816f168751cf1d79730ded3e7e97325d2582a6516436aa165260f576f330535cf28d6f9c26a6f7d"
    "dd74b60e702826392ac9f16a1ccdb5"
)


fragmented_client_hello2 = bytes.fromhex(
    "cd0000000108d520c3803f5de4d3000044bceadc93d1a46ab45f934299ba642a3a4bdac62cf80981105cc546c2"
    "96b78fda0acdec8e8cb8a69e4d3446033f3edd0f52fe02d99c841336402b9c2419852414b9bc6b17128b1c198e"
    "0f2a709895cddef029b738c7a8bf7917162e5709f7fa4933e6a9db5da418db8794e8458dd699eb31752c402cbf"
    "3b6f0d7e6983dba686285a49b4c8724f9653ed4430667a242f4b0613aa37b039226b1c42a1cfaeab40cabbf6be"
    "d7d49cbca3a10e8aced1560e44a22073a9432f39e16d177ecf89c4b3807ac748fed84d9811fe91aad76bf85bc8"
    "c8b1def2985b8cce6226ce441924418f0c4c6895918e86065a3143dda8afce756c7318b3d861a1f0160d0814ef"
    "118389f55198b0c5da4ed6d95a72b6f2a35ffc56bda85753dd146dd6eb29f64b51f7ca7e4e0bf7de82a5041e1f"
    "a4dc7303f5b7dc31901185f787876ce81213a587cbe42bdcab63be1c146798641664fecc477b8112109cb317f6"
    "f6fe1f3e36c2e843ec875ed8631ac7527817ab928c68a16ae672ca56464556a8c4c700c4f40920a028207911f3"
    "2cd2840fce3504ca29f25524b1e9108dbded72ff0364443da17573badc99ad33f6c91baeca3c933258500e7b78"
    "347ce76cf893a85f163698edd6209ac5d990f092cc609ff7faa6a0c2e5f57e4154bec72e2441028ad00cdce202"
    "a07e0e9696578e0c17c152b2880874cad11631db5210efaf260d18dccecd04987f8ceea7e534c381d9aed5be28"
    "8b2086103bd84fd6150037cb0bc1abacd3c2b3f1db213998b4b36e86e46264809fa2757f2b2764c0b94dc222ac"
    "674a9f5c183fb40ef52e7b36ed8f3aaf1fe776643d819fb55284387b83f0ad688461ae8612784b36494585caa5"
    "f05fb391216bedc23b00e759bebe0cd19f1d514b5faba8a061d36204dd7c4e8daf1150ae8441aadbbeff7735ff"
    "613ecb2d1dabf256ffcee5b2ba07f0d2d53c7e98691b261cdadf5fac8ed2985720f7f460a8140fdb094870cc65"
    "4656779bbfc095cd5bc666f18e44e86d765004b16a763c330fc165fdb604038067288d56fbd2e6ead2a7352406"
    "4f6995a54ef529990239065ccf33ab5fa3e56ec2ff15b6981bab32658c5d4184407865f3a0e7c37d8d53ac4850"
    "cfdb16887e04eea4284517b2141c1824babae24207ba14e91eb6a30735f33f664d7fefde94d582c06dd26922a6"
    "6e4657c144ee9f99b7985ba1fd7dceb700cecdcb8950a57fc3b239709e84a4616d8e0f7865025b37d27e5cc7c2"
    "b24b02745a89e12315ff4c4e87ea0d4ff90018f4243de3668b22547ba3a147540582b28152ad9412f0c2aea0c1"
    "c0bf71c4176fed4c1d96853ef1d5db80ce4ba66d67c6998c052ebb2cf05511c54d233c24c2f9ed1ea14c305eba"
    "9aed02ad0f1c48772646bfc4edc3f735cd3c16c885e1c54918e0070e1bcc68d835097fe43183e3ef26ab3d1993"
    "dca6960b6ca0ffb1b90417114e55364211c1bd9688adfbb77ebfd7b7ffe47c45f3813390aeb5020fb63c018641"
    "5a260ae26fab479e170843936d8e786120afa6edacecb32abfbe180237b0684507636fe221b2b980683a9f3610"
    "8619c5ab4e271dd450d855f0085814750347da051a903bfa251b395cdc59356c68a7dae062e770c37f4d14f8b9"
    "dd989248e7449e9b581ef9925d85e06372dd61bcbde872791e71855a5aa0c734d387731dde31d02500e1cd5f51"
    "954f0e999398e6b0762bf6bb6bef9a"
)


def test_error_code_to_str():
    assert error_code_to_str(0x6) == "FINAL_SIZE_ERROR"
    assert error_code_to_str(0x104) == "H3_CLOSED_CRITICAL_STREAM"
    assert error_code_to_str(0xDEAD) == f"unknown error (0xdead)"


def test_is_success_error_code():
    assert is_success_error_code(0x0)
    assert not is_success_error_code(0x6)
    assert is_success_error_code(0x100)
    assert not is_success_error_code(0x104)
    assert not is_success_error_code(0xDEAD)


@pytest.mark.parametrize("value", ["s1 s2\n", "s1 s2"])
def test_secrets_logger(value: str):
    logger = MagicMock()
    quic_logger = QuicSecretsLogger(logger)
    assert quic_logger.write(value) == 6
    quic_logger.flush()
    logger.assert_called_once_with(None, b"s1 s2")


class MockQuic(QuicConnection):
    def __init__(self, event) -> None:
        super().__init__(configuration=QuicConfiguration(is_client=True))
        self.event = event

    def next_event(self):
        event = self.event
        self.event = None
        return event

    def datagrams_to_send(self, now: float):
        return []

    def get_timer(self):
        return None


def make_mock_quic(
    tctx: context.Context,
    event: quic_events.QuicEvent | None = None,
    established: bool = True,
) -> tuple[tutils.Playbook, MockQuic]:
    tctx.client.state = connection.ConnectionState.CLOSED
    quic_layer = QuicLayer(tctx, tctx.client, time=lambda: 0)
    quic_layer.child_layer = TlsEchoLayer(tctx)
    mock = MockQuic(event)
    quic_layer.quic = mock
    quic_layer.tunnel_state = (
        tls.tunnel.TunnelState.OPEN
        if established
        else tls.tunnel.TunnelState.ESTABLISHING
    )
    return tutils.Playbook(quic_layer), mock


class TestQuicLayer:
    @pytest.mark.parametrize("established", [True, False])
    def test_invalid_event(self, tctx: context.Context, established: bool):
        class InvalidEvent(quic_events.QuicEvent):
            pass

        playbook, conn = make_mock_quic(
            tctx, event=InvalidEvent(), established=established
        )
        with pytest.raises(AssertionError, match="Unexpected event"):
            assert playbook >> events.DataReceived(tctx.client, b"")

    def test_invalid_stream_command(self, tctx: context.Context):
        playbook, conn = make_mock_quic(
            tctx, quic_events.DatagramFrameReceived(b"invalid-stream-command")
        )
        with pytest.raises(AssertionError, match="Unexpected stream command"):
            assert playbook >> events.DataReceived(tctx.client, b"")

    def test_close(self, tctx: context.Context):
        playbook, conn = make_mock_quic(
            tctx, quic_events.DatagramFrameReceived(b"close-connection")
        )
        assert not conn._close_event
        assert (
            playbook
            >> events.DataReceived(tctx.client, b"")
            << commands.CloseConnection(tctx.client)
        )
        assert conn._close_event
        assert conn._close_event.error_code == 0

    def test_close_error(self, tctx: context.Context):
        playbook, conn = make_mock_quic(
            tctx, quic_events.DatagramFrameReceived(b"close-connection-error")
        )
        assert not conn._close_event
        assert (
            playbook
            >> events.DataReceived(tctx.client, b"")
            << CloseQuicConnection(tctx.client, 123, None, "error")
        )
        assert conn._close_event
        assert conn._close_event.error_code == 123

    def test_datagram(self, tctx: context.Context):
        playbook, conn = make_mock_quic(
            tctx, quic_events.DatagramFrameReceived(b"packet")
        )
        assert not conn._datagrams_pending
        assert playbook >> events.DataReceived(tctx.client, b"")
        assert len(conn._datagrams_pending) == 1
        assert conn._datagrams_pending[0] == b"packet"

    def test_stream_data(self, tctx: context.Context):
        playbook, conn = make_mock_quic(
            tctx, quic_events.StreamDataReceived(b"packet", False, 42)
        )
        assert 42 not in conn._streams
        assert playbook >> events.DataReceived(tctx.client, b"")
        assert b"packet" == conn._streams[42].sender._buffer

    def test_stream_reset(self, tctx: context.Context):
        playbook, conn = make_mock_quic(tctx, quic_events.StreamReset(123, 42))
        assert 42 not in conn._streams
        assert playbook >> events.DataReceived(tctx.client, b"")
        assert conn._streams[42].sender.reset_pending
        assert conn._streams[42].sender._reset_error_code == 123

    def test_stream_stop(self, tctx: context.Context):
        playbook, conn = make_mock_quic(tctx, quic_events.StopSendingReceived(123, 24))
        assert 24 not in conn._streams
        conn._get_or_create_stream_for_send(24)
        assert playbook >> events.DataReceived(tctx.client, b"")
        assert conn._streams[24].receiver.stop_pending
        assert conn._streams[24].receiver._stop_error_code == 123


class SSLTest:
    """Helper container for QuicConnection object."""

    def __init__(
        self,
        server_side: bool = False,
        alpn: list[str] | None = None,
        sni: str | None = "example.mitmproxy.org",
        version: int | None = None,
        settings: QuicTlsSettings | None = None,
    ):
        if settings is None:
            self.ctx = QuicConfiguration(
                is_client=not server_side,
                max_datagram_frame_size=65536,
            )

            self.ctx.verify_mode = ssl.CERT_OPTIONAL
            self.ctx.load_verify_locations(
                cafile=tdata.path(
                    "mitmproxy/net/data/verificationcerts/trusted-root.crt"
                ),
            )

            if alpn:
                self.ctx.alpn_protocols = alpn
            if server_side:
                if sni == "192.0.2.42":
                    filename = "trusted-leaf-ip"
                else:
                    filename = "trusted-leaf"
                self.ctx.load_cert_chain(
                    certfile=tdata.path(
                        f"mitmproxy/net/data/verificationcerts/{filename}.crt"
                    ),
                    keyfile=tdata.path(
                        f"mitmproxy/net/data/verificationcerts/{filename}.key"
                    ),
                )

            self.ctx.server_name = None if server_side else sni

            if version is not None:
                self.ctx.supported_versions = [version]
        else:
            assert alpn is None
            assert version is None
            self.ctx = tls_settings_to_configuration(
                settings=settings,
                is_client=not server_side,
                server_name=sni,
            )

        self.now = 0.0
        self.address = (sni, 443)
        self.quic = None if server_side else QuicConnection(configuration=self.ctx)
        if not server_side:
            self.quic.connect(self.address, now=self.now)

    def write(self, buf: bytes):
        self.now = self.now + 0.1
        if self.quic is None:
            quic_buf = QuicBuffer(data=buf)
            header = pull_quic_header(quic_buf, host_cid_length=8)
            self.quic = QuicConnection(
                configuration=self.ctx,
                original_destination_connection_id=header.destination_cid,
            )
        self.quic.receive_datagram(buf, self.address, self.now)

    def read(self) -> bytes:
        self.now = self.now + 0.1
        buf = b""
        has_data = False
        for datagram, addr in self.quic.datagrams_to_send(self.now):
            assert addr == self.address
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
            break
    else:
        raise AssertionError()


def finish_handshake(
    playbook: tutils.Playbook,
    conn: connection.Connection,
    tssl: SSLTest,
    child_layer: type[T],
) -> T:
    result: T | None = None

    def set_layer(next_layer: layer.NextLayer) -> None:
        nonlocal result
        result = child_layer(next_layer.context)
        next_layer.layer = result

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
        >> tutils.reply(side_effect=set_layer)
    )
    assert tls_hook_data().conn.error is None
    tssl.write(data())

    assert result
    return result


def reply_tls_start_client(alpn: str | None = None, *args, **kwargs) -> tutils.reply:
    """
    Helper function to simplify the syntax for quic_start_client hooks.
    """

    def make_client_conn(tls_start: QuicTlsData) -> None:
        config = QuicConfiguration()
        config.load_cert_chain(
            tdata.path("mitmproxy/net/data/verificationcerts/trusted-leaf.crt"),
            tdata.path("mitmproxy/net/data/verificationcerts/trusted-leaf.key"),
        )
        tls_start.settings = QuicTlsSettings(
            certificate=config.certificate,
            certificate_chain=config.certificate_chain,
            certificate_private_key=config.private_key,
        )
        if alpn is not None:
            tls_start.settings.alpn_protocols = [alpn]

    return tutils.reply(*args, side_effect=make_client_conn, **kwargs)


def reply_tls_start_server(alpn: str | None = None, *args, **kwargs) -> tutils.reply:
    """
    Helper function to simplify the syntax for quic_start_server hooks.
    """

    def make_server_conn(tls_start: QuicTlsData) -> None:
        tls_start.settings = QuicTlsSettings(
            ca_file=tdata.path("mitmproxy/net/data/verificationcerts/trusted-root.crt"),
            verify_mode=ssl.CERT_REQUIRED,
        )
        if alpn is not None:
            tls_start.settings.alpn_protocols = [alpn]

    return tutils.reply(*args, side_effect=make_server_conn, **kwargs)


class TestServerQuic:
    def test_repr(self, tctx: context.Context):
        assert repr(ServerQuicLayer(tctx, time=lambda: 0))

    def test_not_connected(self, tctx: context.Context):
        """Test that we don't do anything if no server connection exists."""
        layer = ServerQuicLayer(tctx, time=lambda: 0)
        layer.child_layer = TlsEchoLayer(tctx)

        assert (
            tutils.Playbook(layer)
            >> events.DataReceived(tctx.client, b"Hello World")
            << commands.SendData(tctx.client, b"hello world")
        )

    def test_simple(self, tctx: context.Context):
        tssl = SSLTest(server_side=True)

        playbook = tutils.Playbook(ServerQuicLayer(tctx, time=lambda: tssl.now))
        tctx.server.address = ("example.mitmproxy.org", 443)
        tctx.server.state = connection.ConnectionState.OPEN
        tctx.server.sni = "example.mitmproxy.org"

        # send ClientHello, receive ClientHello
        data = tutils.Placeholder(bytes)
        assert (
            playbook
            << QuicStartServerHook(tutils.Placeholder())
            >> reply_tls_start_server()
            << commands.SendData(tctx.server, data)
            << commands.RequestWakeup(0.2)
        )
        tssl.write(data())
        assert not tssl.handshake_completed()

        # finish handshake (mitmproxy)
        echo = finish_handshake(playbook, tctx.server, tssl, TlsEchoLayer)

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
        _test_echo(playbook, tssl, tctx.server)

        tssl.quic.close(42, None, "goodbye from simple")
        playbook >> events.DataReceived(tctx.server, tssl.read())
        playbook << None
        assert playbook
        tssl.now = tssl.now + 60
        assert (
            playbook
            >> tutils.reply(to=commands.RequestWakeup)
            << commands.CloseConnection(tctx.server)
            >> events.ConnectionClosed(tctx.server)
            << None
        )
        assert echo.closed
        assert echo.closed.error_code == 42
        assert echo.closed.reason_phrase == "goodbye from simple"

    def test_untrusted_cert(self, tctx: context.Context):
        """If the certificate is not trusted, we should fail."""
        tssl = SSLTest(server_side=True)

        playbook = tutils.Playbook(ServerQuicLayer(tctx, time=lambda: tssl.now))
        tctx.server.address = ("wrong.host.mitmproxy.org", 443)
        tctx.server.sni = "wrong.host.mitmproxy.org"

        # send ClientHello
        data = tutils.Placeholder(bytes)
        assert (
            playbook
            << layer.NextLayerHook(tutils.Placeholder())
            >> tutils.reply_next_layer(TlsEchoLayer)
            >> events.DataReceived(tctx.client, b"open-connection")
            << commands.OpenConnection(tctx.server)
            >> tutils.reply(None)
            << QuicStartServerHook(tutils.Placeholder())
            >> reply_tls_start_server()
            << commands.SendData(tctx.server, data)
            << commands.RequestWakeup(0.2)
        )

        # receive ServerHello, finish client handshake
        tssl.write(data())
        assert not tssl.handshake_completed()

        # exchange termination data
        data = tutils.Placeholder(bytes)
        assert (
            playbook
            >> events.DataReceived(tctx.server, tssl.read())
            << commands.SendData(tctx.server, data)
        )
        tssl.write(data())
        tssl.now = tssl.now + 60

        tls_hook_data = tutils.Placeholder(QuicTlsData)
        assert (
            playbook
            >> tutils.reply(to=commands.RequestWakeup)
            << commands.Log(
                tutils.StrMatching(
                    "Server QUIC handshake failed. hostname 'wrong.host.mitmproxy.org' doesn't match"
                ),
                WARNING,
            )
            << tls.TlsFailedServerHook(tls_hook_data)
            >> tutils.reply()
            << commands.CloseConnection(tctx.server)
            << commands.SendData(
                tctx.client,
                tutils.BytesMatching(
                    b"open-connection failed: hostname 'wrong.host.mitmproxy.org' doesn't match"
                ),
            )
        )
        assert tls_hook_data().conn.error.startswith(
            "hostname 'wrong.host.mitmproxy.org' doesn't match"
        )
        assert not tctx.server.tls_established


def make_client_tls_layer(
    tctx: context.Context, no_server: bool = False, **kwargs
) -> tuple[tutils.Playbook, ClientQuicLayer, SSLTest]:
    tssl_client = SSLTest(**kwargs)

    # This is a bit contrived as the client layer expects a server layer as parent.
    # We also set child layers manually to avoid NextLayer noise.
    server_layer = (
        DummyLayer(tctx)
        if no_server
        else ServerQuicLayer(tctx, time=lambda: tssl_client.now)
    )
    client_layer = ClientQuicLayer(tctx, time=lambda: tssl_client.now)
    server_layer.child_layer = client_layer
    playbook = tutils.Playbook(server_layer)

    # Add some server config, this is needed anyways.
    tctx.server.__dict__["address"] = (
        "example.mitmproxy.org",
        443,
    )  # .address fails because connection is open
    tctx.server.sni = "example.mitmproxy.org"

    # Start handshake.
    assert not tssl_client.handshake_completed()

    return playbook, client_layer, tssl_client


class TestClientQuic:
    def test_http3_disabled(self, tctx: context.Context):
        """Test that we swallow QUIC packets if QUIC and HTTP/3 are disabled."""
        tctx.options.http3 = False
        assert (
            tutils.Playbook(ClientQuicLayer(tctx, time=time.time), logs=True)
            >> events.DataReceived(tctx.client, client_hello)
            << commands.Log(
                "Swallowing QUIC handshake because HTTP/3 is disabled.", DEBUG
            )
            << None
        )

    def test_client_only(self, tctx: context.Context):
        """Test QUIC with client only"""
        playbook, client_layer, tssl_client = make_client_tls_layer(tctx)
        client_layer.debug = "  "
        assert not tctx.client.tls_established

        # Send ClientHello, receive ServerHello
        data = tutils.Placeholder(bytes)
        assert (
            playbook
            >> events.DataReceived(tctx.client, tssl_client.read())
            << tls.TlsClienthelloHook(tutils.Placeholder())
            >> tutils.reply()
            << QuicStartClientHook(tutils.Placeholder())
            >> reply_tls_start_client()
            << commands.SendData(tctx.client, data)
            << commands.RequestWakeup(tutils.Placeholder())
        )
        tssl_client.write(data())
        assert tssl_client.handshake_completed()
        # Finish Handshake
        finish_handshake(playbook, tctx.client, tssl_client, TlsEchoLayer)

        assert tssl_client.quic.tls._peer_certificate
        assert tctx.client.tls_established

        # Echo
        _test_echo(playbook, tssl_client, tctx.client)
        other_server = connection.Server(address=None)
        assert (
            playbook
            >> events.DataReceived(other_server, b"Plaintext")
            << commands.SendData(other_server, b"plaintext")
        )

        # test the close log
        tssl_client.now = tssl_client.now + 60
        assert (
            playbook
            >> tutils.reply(to=commands.RequestWakeup)
            << commands.Log(
                tutils.StrMatching(
                    r"  >> Wakeup\(command=RequestWakeup\({'delay': [.\d]+}\)\)"
                ),
                DEBUG,
            )
            << commands.Log(
                "  [quic] close_notify Client(client:1234, state=open, tls) (reason=Idle timeout)",
                DEBUG,
            )
            << commands.CloseConnection(tctx.client)
        )

    @pytest.mark.parametrize("server_state", ["open", "closed"])
    def test_server_required(
        self, tctx: context.Context, server_state: Literal["open", "closed"]
    ):
        """
        Test the scenario where a server connection is required (for example, because of an unknown ALPN)
        to establish TLS with the client.
        """
        if server_state == "open":
            tctx.server.state = connection.ConnectionState.OPEN
        tssl_server = SSLTest(server_side=True, alpn=["quux"])
        playbook, client_layer, tssl_client = make_client_tls_layer(tctx, alpn=["quux"])

        # We should now get instructed to open a server connection.
        data = tutils.Placeholder(bytes)

        def require_server_conn(client_hello: tls.ClientHelloData) -> None:
            client_hello.establish_server_tls_first = True

        (
            playbook
            >> events.DataReceived(tctx.client, tssl_client.read())
            << tls.TlsClienthelloHook(tutils.Placeholder())
            >> tutils.reply(side_effect=require_server_conn)
        )
        if server_state == "closed":
            playbook << commands.OpenConnection(tctx.server)
            playbook >> tutils.reply(None)
        assert (
            playbook
            << QuicStartServerHook(tutils.Placeholder())
            >> reply_tls_start_server(alpn="quux")
            << commands.SendData(tctx.server, data)
            << commands.RequestWakeup(tutils.Placeholder())
        )

        # Establish TLS with the server...
        tssl_server.write(data())
        assert not tssl_server.handshake_completed()

        data = tutils.Placeholder(bytes)
        assert (
            playbook
            >> events.DataReceived(tctx.server, tssl_server.read())
            << tls.TlsEstablishedServerHook(tutils.Placeholder())
            >> tutils.reply()
            << commands.SendData(tctx.server, data)
            << commands.RequestWakeup(tutils.Placeholder())
            << QuicStartClientHook(tutils.Placeholder())
        )
        tssl_server.write(data())
        assert tctx.server.tls_established
        # Server TLS is established, we can now reply to the client handshake...

        data = tutils.Placeholder(bytes)
        assert (
            playbook
            >> reply_tls_start_client(alpn="quux")
            << commands.SendData(tctx.client, data)
            << commands.RequestWakeup(tutils.Placeholder())
        )
        tssl_client.write(data())
        assert tssl_client.handshake_completed()
        finish_handshake(playbook, tctx.client, tssl_client, TlsEchoLayer)

        # Both handshakes completed!
        assert tctx.client.tls_established
        assert tctx.server.tls_established
        assert tctx.server.sni == tctx.client.sni
        assert tctx.client.alpn == b"quux"
        assert tctx.server.alpn == b"quux"
        _test_echo(playbook, tssl_client, tctx.client)
        _test_echo(playbook, tssl_server, tctx.server)

    @pytest.mark.parametrize("server_state", ["open", "closed"])
    def test_passthrough_from_clienthello(
        self, tctx: context.Context, server_state: Literal["open", "closed"]
    ):
        """
        Test the scenario where the connection is moved to passthrough mode in the tls_clienthello hook.
        """
        if server_state == "open":
            tctx.server.timestamp_start = time.time()
            tctx.server.state = connection.ConnectionState.OPEN

        playbook, client_layer, tssl_client = make_client_tls_layer(tctx, alpn=["quux"])
        client_layer.child_layer = TlsEchoLayer(client_layer.context)

        def make_passthrough(client_hello: tls.ClientHelloData) -> None:
            client_hello.ignore_connection = True

        client_hello = tssl_client.read()
        (
            playbook
            >> events.DataReceived(tctx.client, client_hello)
            << tls.TlsClienthelloHook(tutils.Placeholder())
            >> tutils.reply(side_effect=make_passthrough)
        )
        if server_state == "closed":
            playbook << commands.OpenConnection(tctx.server)
            playbook >> tutils.reply(None)
        assert (
            playbook
            << commands.SendData(tctx.server, client_hello)  # passed through unmodified
            >> events.DataReceived(
                tctx.server, b"ServerHello"
            )  # and the same for the serverhello.
            << commands.SendData(tctx.client, b"ServerHello")
        )

    @pytest.mark.parametrize(
        "fragments",
        [
            [fragmented_client_hello1, fragmented_client_hello2],
            [fragmented_client_hello2, fragmented_client_hello1],
        ],
    )
    def test_fragmented_client_hello(
        self, tctx: context.Context, fragments: list[bytes]
    ):
        client_layer = ClientQuicLayer(tctx, time=time.time)
        playbook = tutils.Playbook(client_layer)

        assert not tctx.client.sni

        assert (
            playbook
            >> events.Start()
            >> events.DataReceived(tctx.client, fragments[0])
            >> events.DataReceived(tctx.client, fragments[1])
            << tls.TlsClienthelloHook(tutils.Placeholder())
            >> tutils.reply()
            << QuicStartClientHook(tutils.Placeholder())
        )

        assert tctx.client.sni == "localhost"

    @pytest.mark.parametrize(
        "data,err",
        [
            (b"\x16\x03\x01\x00\x00", "Packet fixed bit is zero (1603010000)"),
            (b"test", "Malformed head (74657374)"),
        ],
    )
    def test_cannot_parse_clienthello(
        self, tctx: context.Context, data: bytes, err: str
    ):
        """Test the scenario where we cannot parse the ClientHello"""
        playbook, client_layer, tssl_client = make_client_tls_layer(tctx)
        tls_hook_data = tutils.Placeholder(QuicTlsData)

        assert (
            playbook
            >> events.DataReceived(tctx.client, data)
            << commands.Log(
                f"Client QUIC handshake failed. Cannot parse QUIC header: {err}",
                level=WARNING,
            )
            << tls.TlsFailedClientHook(tls_hook_data)
            >> tutils.reply()
            << commands.CloseConnection(tctx.client)
        )
        assert tls_hook_data().conn.error
        assert not tctx.client.tls_established

        # Make sure that an active server connection does not cause child layers to spawn.
        client_layer.debug = ""
        assert (
            playbook
            >> events.DataReceived(
                connection.Server(address=None), b"data on other stream"
            )
            << commands.Log(">> DataReceived(server, b'data on other stream')", DEBUG)
            << commands.Log(
                "[quic] Swallowing DataReceived(server, b'data on other stream') as handshake failed.",
                DEBUG,
            )
        )

    def test_mitmproxy_ca_is_untrusted(self, tctx: context.Context):
        """Test the scenario where the client doesn't trust the mitmproxy CA."""
        playbook, client_layer, tssl_client = make_client_tls_layer(
            tctx, sni="wrong.host.mitmproxy.org"
        )
        playbook.logs = True

        data = tutils.Placeholder(bytes)
        assert (
            playbook
            >> events.DataReceived(tctx.client, tssl_client.read())
            << tls.TlsClienthelloHook(tutils.Placeholder())
            >> tutils.reply()
            << QuicStartClientHook(tutils.Placeholder())
            >> reply_tls_start_client()
            << commands.SendData(tctx.client, data)
            << commands.RequestWakeup(tutils.Placeholder())
        )
        tssl_client.write(data())
        assert not tssl_client.handshake_completed()

        # Finish Handshake
        tls_hook_data = tutils.Placeholder(QuicTlsData)
        playbook >> events.DataReceived(tctx.client, tssl_client.read())
        assert playbook
        tssl_client.now = tssl_client.now + 60
        assert (
            playbook
            >> tutils.reply(to=commands.RequestWakeup)
            << commands.Log(
                tutils.StrMatching(
                    "Client QUIC handshake failed. hostname 'wrong.host.mitmproxy.org' doesn't match"
                ),
                WARNING,
            )
            << tls.TlsFailedClientHook(tls_hook_data)
            >> tutils.reply()
            << commands.CloseConnection(tctx.client)
            >> events.ConnectionClosed(tctx.client)
        )
        assert not tctx.client.tls_established
        assert tls_hook_data().conn.error

    def test_server_unavailable_and_no_settings(self, tctx: context.Context):
        playbook, client_layer, tssl_client = make_client_tls_layer(tctx)

        def require_server_conn(client_hello: tls.ClientHelloData) -> None:
            client_hello.establish_server_tls_first = True

        assert (
            playbook
            >> events.DataReceived(tctx.client, tssl_client.read())
            << tls.TlsClienthelloHook(tutils.Placeholder())
            >> tutils.reply(side_effect=require_server_conn)
            << commands.OpenConnection(tctx.server)
            >> tutils.reply("I cannot open the server, Dave")
            << commands.Log(
                f"Unable to establish QUIC connection with server (I cannot open the server, Dave). "
                f"Trying to establish QUIC with client anyway. "
                f"If you plan to redirect requests away from this server, "
                f"consider setting `connection_strategy` to `lazy` to suppress early connections."
            )
            << QuicStartClientHook(tutils.Placeholder())
        )
        tctx.client.state = connection.ConnectionState.CLOSED
        assert (
            playbook
            >> tutils.reply()
            << commands.Log(f"No QUIC context was provided, failing connection.", ERROR)
            << commands.CloseConnection(tctx.client)
            << commands.Log(
                "Client QUIC handshake failed. connection closed early", WARNING
            )
            << tls.TlsFailedClientHook(tutils.Placeholder())
        )

    def test_no_server_tls(self, tctx: context.Context):
        playbook, client_layer, tssl_client = make_client_tls_layer(
            tctx, no_server=True
        )

        def require_server_conn(client_hello: tls.ClientHelloData) -> None:
            client_hello.establish_server_tls_first = True

        assert (
            playbook
            >> events.DataReceived(tctx.client, tssl_client.read())
            << tls.TlsClienthelloHook(tutils.Placeholder())
            >> tutils.reply(side_effect=require_server_conn)
            << commands.Log(
                f"Unable to establish QUIC connection with server (No server QUIC available.). "
                f"Trying to establish QUIC with client anyway. "
                f"If you plan to redirect requests away from this server, "
                f"consider setting `connection_strategy` to `lazy` to suppress early connections."
            )
            << QuicStartClientHook(tutils.Placeholder())
        )

    def test_version_negotiation(self, tctx: context.Context):
        # To trigger a version negotiation, use one of the reserved 0x?A?A?A?A versions.
        # https://datatracker.ietf.org/doc/html/rfc9000#section-15
        playbook, client_layer, tssl_client = make_client_tls_layer(
            tctx, version=0x1A2A3A4A
        )
        assert (
            playbook
            >> events.DataReceived(tctx.client, tssl_client.read())
            << commands.SendData(tctx.client, tutils.Placeholder())
        )
        assert client_layer.tunnel_state == tls.tunnel.TunnelState.ESTABLISHING

    def test_non_init_clienthello(self, tctx: context.Context):
        playbook, client_layer, tssl_client = make_client_tls_layer(tctx)
        data = (
            b"\xc2\x00\x00\x00\x01\x08q\xda\x98\x03X-\x13o\x08y\xa5RQv\xbe\xe3\xeb\x00@a\x98\x19\xf95t\xad-\x1c\\a\xdd\x8c\xd0\x15F"
            b"\xdf\xdc\x87cb\x1eu\xb0\x95*\xac\xa8\xf7a \xb8\nQ\xbd=\xf5x\xca\r\xe6\x8b\x05 w\x9f\xcd\x8d\xcb\xa0\x06\x1e \x8d.\x8f"
            b"T\xda\x12et\xe4\x83\x93X<o\xad\xd5%&\x8f7\xa6>\x8aa\xd1\xb2\x18\xb6\xa7\xf50y\x9b\xc5T\xe1\x87\xdd\x9fqv\xb0\x90\xa7s"
            b"\xee\x00\x00\x00\x01\x08q\xda\x98\x03X-\x13o\x08y\xa5RQv\xbe\xe3\xeb@a*.\xa8j\x90\x1b\x1a\x7fZ\x04\x0b\\\xc7\x00\x03"
            b"\xd7sC\xf8G\x84\x1e\xba\xcf\x08Z\xdd\x98+\xaa\x98J\xca\xe3\xb7u1\x89\x00\xdf\x8e\x16`\xd9^\xc0@i\x1a\x10\x99\r\xd8"
            b"\x1dv3\xc6\xb8\"\xb9\xa8F\x95K\x9a/\xbc'\xd8\xd8\x94\x8f\xe7B/\x05\x9d\xfb\x80\xa9\xda@\xe6\xb0J\xfe\xe0\x0f\x02L}"
            b"\xd9\xed\xd2L\xa7\xcf"
        )
        assert (
            playbook
            >> events.DataReceived(tctx.client, data)
            << commands.Log(
                f"Client QUIC handshake failed. Invalid handshake received, roaming not supported. ({data.hex()})",
                WARNING,
            )
            << tls.TlsFailedClientHook(tutils.Placeholder())
        )
        assert client_layer.tunnel_state == tls.tunnel.TunnelState.ESTABLISHING

    def test_invalid_clienthello(self, tctx: context.Context):
        playbook, client_layer, tssl_client = make_client_tls_layer(tctx)
        data = client_hello[0:1200] + b"\x00" + client_hello[1200:]
        assert (
            playbook
            >> events.DataReceived(tctx.client, data)
            << commands.Log(
                f"Client QUIC handshake failed. Cannot parse ClientHello: Invalid ClientHello packet: payload_decrypt_error ({data.hex()})",
                WARNING,
            )
            << tls.TlsFailedClientHook(tutils.Placeholder())
        )
        assert client_layer.tunnel_state == tls.tunnel.TunnelState.ESTABLISHING

    def test_invalid_fragmented_clienthello(self, tctx: context.Context):
        client_layer = ClientQuicLayer(tctx, time=time.time)
        playbook = tutils.Playbook(client_layer)

        assert not tctx.client.sni

        invalid_frag2 = (
            fragmented_client_hello2[:300] + b"\x00" + fragmented_client_hello2[300:]
        )
        data = fragmented_client_hello1 + b"\n" + invalid_frag2

        assert (
            playbook
            >> events.Start()
            >> events.DataReceived(tctx.client, fragmented_client_hello1)
            >> events.DataReceived(tctx.client, invalid_frag2)
            << commands.Log(
                f"Client QUIC handshake failed. Cannot parse ClientHello: Invalid ClientHello packet: payload_decrypt_error ({data.hex()})",
                WARNING,
            )
            << tls.TlsFailedClientHook(tutils.Placeholder())
        )
        assert client_layer.tunnel_state == tls.tunnel.TunnelState.ESTABLISHING

    def test_tls_reset(self, tctx: context.Context):
        tctx.client.tls = True
        tctx.client.sni = "some"
        DummyLayer(tctx)
        ClientQuicLayer(tctx, time=lambda: 0)
        assert tctx.client.sni is None
