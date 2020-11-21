import pytest

from mitmproxy.proxy2 import commands, events, layer
from test.mitmproxy.proxy2 import tutils


class TestNextLayer:
    def test_simple(self, tctx):
        nl = layer.NextLayer(tctx)
        playbook = tutils.Playbook(nl, hooks=True)

        assert (
            playbook
            >> events.DataReceived(tctx.client, b"foo")
            << layer.NextLayerHook(nl)
            >> tutils.reply()
            >> events.DataReceived(tctx.client, b"bar")
            << layer.NextLayerHook(nl)
        )
        assert nl.data_client() == b"foobar"
        assert nl.data_server() == b""

        nl.layer = tutils.EchoLayer(tctx)
        assert (
            playbook
            >> tutils.reply()
            << commands.SendData(tctx.client, b"foo")
            << commands.SendData(tctx.client, b"bar")
        )

    def test_late_hook_reply(self, tctx):
        """
        Properly handle case where we receive an additional event while we are waiting for
        a reply from the proxy core.
        """
        nl = layer.NextLayer(tctx)
        playbook = tutils.Playbook(nl)

        assert (
            playbook
            >> events.DataReceived(tctx.client, b"foo")
            << layer.NextLayerHook(nl)
            >> events.DataReceived(tctx.client, b"bar")
        )
        assert nl.data_client() == b"foo"  # "bar" is paused.
        nl.layer = tutils.EchoLayer(tctx)

        assert (
            playbook
            >> tutils.reply(to=-2)
            << commands.SendData(tctx.client, b"foo")
            << commands.SendData(tctx.client, b"bar")
        )

    @pytest.mark.parametrize("layer_found", [True, False])
    def test_receive_close(self, tctx, layer_found):
        """Test that we abort a client connection which has disconnected without any layer being found."""
        nl = layer.NextLayer(tctx)
        playbook = tutils.Playbook(nl)
        assert (
            playbook
            >> events.DataReceived(tctx.client, b"foo")
            << layer.NextLayerHook(nl)
            >> events.ConnectionClosed(tctx.client)
        )
        if layer_found:
            nl.layer = tutils.RecordLayer(tctx)
            assert (
                playbook
                >> tutils.reply(to=-2)
            )
            assert isinstance(nl.layer.event_log[-1], events.ConnectionClosed)
        else:
            assert (
                playbook
                >> tutils.reply(to=-2)
                << commands.CloseConnection(tctx.client)
            )

    def test_func_references(self, tctx):
        nl = layer.NextLayer(tctx)
        playbook = tutils.Playbook(nl)

        assert (
            playbook
            >> events.DataReceived(tctx.client, b"foo")
            << layer.NextLayerHook(nl)
        )
        nl.layer = tutils.EchoLayer(tctx)
        handle = nl.handle_event
        assert (
            playbook
            >> tutils.reply()
            << commands.SendData(tctx.client, b"foo")
        )
        sd, = handle(events.DataReceived(tctx.client, b"bar"))
        assert isinstance(sd, commands.SendData)

    def test_repr(self, tctx):
        nl = layer.NextLayer(tctx)
        nl.layer = tutils.EchoLayer(tctx)
        assert repr(nl)
