from mitmproxy.proxy2 import layer, events, commands
from test.mitmproxy.proxy2 import tutils


class TestNextLayer:
    def test_simple(self, tctx):
        nl = layer.NextLayer(tctx)
        playbook = tutils.playbook(nl, hooks=True)

        assert (
            playbook
            >> events.DataReceived(tctx.client, b"foo")
            << commands.Hook("next_layer", nl)
            >> tutils.reply()
            >> events.DataReceived(tctx.client, b"bar")
            << commands.Hook("next_layer", nl)
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
        playbook = tutils.playbook(nl)

        assert (
            playbook
            >> events.DataReceived(tctx.client, b"foo")
            << commands.Hook("next_layer", nl)
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

    def test_func_references(self, tctx):
        nl = layer.NextLayer(tctx)
        playbook = tutils.playbook(nl)

        assert (
            playbook
            >> events.DataReceived(tctx.client, b"foo")
            << commands.Hook("next_layer", nl)
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
