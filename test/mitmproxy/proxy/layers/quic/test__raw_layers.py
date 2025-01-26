import pytest

from mitmproxy import connection
from mitmproxy.proxy import commands
from mitmproxy.proxy import context
from mitmproxy.proxy import events
from mitmproxy.proxy import layer
from mitmproxy.proxy import layers
from mitmproxy.proxy import tunnel
from mitmproxy.proxy.layers import tcp
from mitmproxy.proxy.layers import udp
from mitmproxy.proxy.layers.quic._commands import CloseQuicConnection
from mitmproxy.proxy.layers.quic._commands import ResetQuicStream
from mitmproxy.proxy.layers.quic._commands import SendQuicStreamData
from mitmproxy.proxy.layers.quic._commands import StopSendingQuicStream
from mitmproxy.proxy.layers.quic._events import QuicConnectionClosed
from mitmproxy.proxy.layers.quic._events import QuicStreamDataReceived
from mitmproxy.proxy.layers.quic._events import QuicStreamEvent
from mitmproxy.proxy.layers.quic._events import QuicStreamReset
from mitmproxy.proxy.layers.quic._raw_layers import QuicStreamLayer
from mitmproxy.proxy.layers.quic._raw_layers import RawQuicLayer
from mitmproxy.tcp import TCPFlow
from mitmproxy.udp import UDPFlow
from mitmproxy.udp import UDPMessage
from test.mitmproxy.proxy import tutils
from test.mitmproxy.proxy.layers.quic.test__stream_layers import TlsEchoLayer


class TestQuicStreamLayer:
    def test_force_raw(self, tctx: context.Context):
        quic_layer = QuicStreamLayer(tctx, True, 1)
        assert isinstance(quic_layer.child_layer, layers.TCPLayer)
        quic_layer.child_layer.flow = TCPFlow(tctx.client, tctx.server)
        quic_layer.refresh_metadata()
        assert quic_layer.child_layer.flow.metadata["quic_is_unidirectional"] is False
        assert quic_layer.child_layer.flow.metadata["quic_initiator"] == "server"
        assert quic_layer.child_layer.flow.metadata["quic_stream_id_client"] == 1
        assert quic_layer.child_layer.flow.metadata["quic_stream_id_server"] is None
        assert quic_layer.stream_id(True) == 1
        assert quic_layer.stream_id(False) is None

    def test_simple(self, tctx: context.Context):
        quic_layer = QuicStreamLayer(tctx, False, 2)
        assert isinstance(quic_layer.child_layer, layer.NextLayer)
        tunnel_layer = tunnel.TunnelLayer(tctx, tctx.client, tctx.server)
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


class TestRawQuicLayer:
    @pytest.mark.parametrize("force_raw", [True, False])
    def test_error(self, tctx: context.Context, force_raw: bool):
        quic_layer = RawQuicLayer(tctx, force_raw=force_raw)
        assert (
            tutils.Playbook(quic_layer)
            << commands.OpenConnection(tctx.server)
            >> tutils.reply("failed to open")
            << commands.CloseConnection(tctx.client)
        )
        assert quic_layer._handle_event == quic_layer.done

    def test_force_raw(self, tctx: context.Context):
        quic_layer = RawQuicLayer(tctx, force_raw=True)
        assert (
            tutils.Playbook(quic_layer, hooks=False)
            << commands.OpenConnection(tctx.server)
            >> tutils.reply(None)
            >> events.DataReceived(tctx.client, b"msg1")
            << commands.SendData(tctx.server, b"msg1")
            >> events.DataReceived(tctx.server, b"msg2")
            << commands.SendData(tctx.client, b"msg2")
            >> QuicStreamDataReceived(tctx.client, 0, b"msg3", end_stream=False)
            << SendQuicStreamData(tctx.server, 0, b"msg3", end_stream=False)
            >> QuicStreamDataReceived(tctx.client, 6, b"msg4", end_stream=False)
            << SendQuicStreamData(tctx.server, 2, b"msg4", end_stream=False)
            >> QuicStreamDataReceived(tctx.server, 9, b"msg5", end_stream=False)
            << SendQuicStreamData(tctx.client, 1, b"msg5", end_stream=False)
            >> QuicStreamDataReceived(tctx.client, 0, b"", end_stream=True)
            << SendQuicStreamData(tctx.server, 0, b"", end_stream=True)
            >> QuicStreamReset(tctx.client, 6, 142)
            << ResetQuicStream(tctx.server, 2, 142)
            >> QuicConnectionClosed(tctx.client, 42, None, "closed")
            << CloseQuicConnection(tctx.server, 42, None, "closed")
            >> QuicConnectionClosed(tctx.server, 42, None, "closed")
            << None
        )
        assert quic_layer._handle_event == quic_layer.done

    def test_msg_inject(self, tctx: context.Context):
        udpflow = tutils.Placeholder(UDPFlow)
        playbook = tutils.Playbook(RawQuicLayer(tctx))
        assert (
            playbook
            << commands.OpenConnection(tctx.server)
            >> tutils.reply(None)
            >> events.DataReceived(tctx.client, b"msg1")
            << layer.NextLayerHook(tutils.Placeholder())
            >> tutils.reply_next_layer(udp.UDPLayer)
            << udp.UdpStartHook(udpflow)
            >> tutils.reply()
            << udp.UdpMessageHook(udpflow)
            >> tutils.reply()
            << commands.SendData(tctx.server, b"msg1")
            >> udp.UdpMessageInjected(udpflow, UDPMessage(True, b"msg2"))
            << udp.UdpMessageHook(udpflow)
            >> tutils.reply()
            << commands.SendData(tctx.server, b"msg2")
            >> udp.UdpMessageInjected(
                UDPFlow(("other", 80), tctx.server), UDPMessage(True, b"msg3")
            )
            << udp.UdpMessageHook(udpflow)
            >> tutils.reply()
            << commands.SendData(tctx.server, b"msg3")
        )
        with pytest.raises(AssertionError, match="not associated"):
            playbook >> udp.UdpMessageInjected(
                UDPFlow(("notfound", 0), ("noexist", 0)), UDPMessage(True, b"msg2")
            )
            assert playbook

    def test_reset_with_end_hook(self, tctx: context.Context):
        tcpflow = tutils.Placeholder(TCPFlow)
        assert (
            tutils.Playbook(RawQuicLayer(tctx))
            << commands.OpenConnection(tctx.server)
            >> tutils.reply(None)
            >> QuicStreamDataReceived(tctx.client, 2, b"msg1", end_stream=False)
            << layer.NextLayerHook(tutils.Placeholder())
            >> tutils.reply_next_layer(tcp.TCPLayer)
            << tcp.TcpStartHook(tcpflow)
            >> tutils.reply()
            << tcp.TcpMessageHook(tcpflow)
            >> tutils.reply()
            << SendQuicStreamData(tctx.server, 2, b"msg1", end_stream=False)
            >> QuicStreamReset(tctx.client, 2, 42)
            << ResetQuicStream(tctx.server, 2, 42)
            << tcp.TcpEndHook(tcpflow)
            >> tutils.reply()
        )

    def test_close_with_end_hooks(self, tctx: context.Context):
        udpflow = tutils.Placeholder(UDPFlow)
        tcpflow = tutils.Placeholder(TCPFlow)
        assert (
            tutils.Playbook(RawQuicLayer(tctx))
            << commands.OpenConnection(tctx.server)
            >> tutils.reply(None)
            >> events.DataReceived(tctx.client, b"msg1")
            << layer.NextLayerHook(tutils.Placeholder())
            >> tutils.reply_next_layer(udp.UDPLayer)
            << udp.UdpStartHook(udpflow)
            >> tutils.reply()
            << udp.UdpMessageHook(udpflow)
            >> tutils.reply()
            << commands.SendData(tctx.server, b"msg1")
            >> QuicStreamDataReceived(tctx.client, 2, b"msg2", end_stream=False)
            << layer.NextLayerHook(tutils.Placeholder())
            >> tutils.reply_next_layer(tcp.TCPLayer)
            << tcp.TcpStartHook(tcpflow)
            >> tutils.reply()
            << tcp.TcpMessageHook(tcpflow)
            >> tutils.reply()
            << SendQuicStreamData(tctx.server, 2, b"msg2", end_stream=False)
            >> QuicConnectionClosed(tctx.client, 42, None, "bye")
            << CloseQuicConnection(tctx.server, 42, None, "bye")
            << udp.UdpEndHook(udpflow)
            << tcp.TcpEndHook(tcpflow)
            >> tutils.reply(to=-2)
            >> tutils.reply(to=-2)
            >> QuicConnectionClosed(tctx.server, 42, None, "bye")
        )

    def test_invalid_stream_event(self, tctx: context.Context):
        playbook = tutils.Playbook(RawQuicLayer(tctx))
        assert (
            tutils.Playbook(RawQuicLayer(tctx))
            << commands.OpenConnection(tctx.server)
            >> tutils.reply(None)
        )
        with pytest.raises(AssertionError, match="Unexpected stream event"):

            class InvalidStreamEvent(QuicStreamEvent):
                pass

            playbook >> InvalidStreamEvent(tctx.client, 0)
            assert playbook

    def test_invalid_event(self, tctx: context.Context):
        playbook = tutils.Playbook(RawQuicLayer(tctx))
        assert (
            tutils.Playbook(RawQuicLayer(tctx))
            << commands.OpenConnection(tctx.server)
            >> tutils.reply(None)
        )
        with pytest.raises(AssertionError, match="Unexpected event"):

            class InvalidEvent(events.Event):
                pass

            playbook >> InvalidEvent()
            assert playbook

    def test_full_close(self, tctx: context.Context):
        assert (
            tutils.Playbook(RawQuicLayer(tctx))
            << commands.OpenConnection(tctx.server)
            >> tutils.reply(None)
            >> QuicStreamDataReceived(tctx.client, 0, b"msg1", end_stream=True)
            << layer.NextLayerHook(tutils.Placeholder())
            >> tutils.reply_next_layer(lambda ctx: udp.UDPLayer(ctx, ignore=True))
            << SendQuicStreamData(tctx.server, 0, b"msg1", end_stream=False)
            << SendQuicStreamData(tctx.server, 0, b"", end_stream=True)
            << StopSendingQuicStream(tctx.server, 0, 0)
        )

    def test_open_connection(self, tctx: context.Context):
        server = connection.Server(address=("other", 80))

        def echo_new_server(ctx: context.Context):
            echo_layer = TlsEchoLayer(ctx)
            echo_layer.context.server = server
            return echo_layer

        assert (
            tutils.Playbook(RawQuicLayer(tctx))
            << commands.OpenConnection(tctx.server)
            >> tutils.reply(None)
            >> QuicStreamDataReceived(
                tctx.client, 0, b"open-connection", end_stream=False
            )
            << layer.NextLayerHook(tutils.Placeholder())
            >> tutils.reply_next_layer(echo_new_server)
            << commands.OpenConnection(server)
            >> tutils.reply("uhoh")
            << SendQuicStreamData(
                tctx.client, 0, b"open-connection failed: uhoh", end_stream=False
            )
        )

    def test_invalid_connection_command(self, tctx: context.Context):
        playbook = tutils.Playbook(RawQuicLayer(tctx))
        assert (
            playbook
            << commands.OpenConnection(tctx.server)
            >> tutils.reply(None)
            >> QuicStreamDataReceived(tctx.client, 0, b"msg1", end_stream=False)
            << layer.NextLayerHook(tutils.Placeholder())
            >> tutils.reply_next_layer(TlsEchoLayer)
            << SendQuicStreamData(tctx.client, 0, b"msg1", end_stream=False)
        )
        with pytest.raises(
            AssertionError, match="Unexpected stream connection command"
        ):
            playbook >> QuicStreamDataReceived(
                tctx.client, 0, b"invalid-command", end_stream=False
            )
            assert playbook
