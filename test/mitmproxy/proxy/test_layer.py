import pytest

from mitmproxy.proxy import commands, events, layer
from mitmproxy.proxy.context import Context
from test.mitmproxy.proxy import tutils


class TestLayer:
    def test_continue(self, tctx: Context):
        class TLayer(layer.Layer):
            def _handle_event(self, event: events.Event) -> layer.CommandGenerator[None]:
                yield commands.OpenConnection(self.context.server)
                yield commands.OpenConnection(self.context.server)

        assert (
            tutils.Playbook(TLayer(tctx))
            << commands.OpenConnection(tctx.server)
            >> tutils.reply(None)
            << commands.OpenConnection(tctx.server)
            >> tutils.reply(None)
        )

    def test_debug_messages(self, tctx: Context):
        tctx.server.id = "serverid"

        class TLayer(layer.Layer):
            debug = " "

            def _handle_event(self, event: events.Event) -> layer.CommandGenerator[None]:
                yield from self.state(event)

            def state_foo(self, event: events.Event) -> layer.CommandGenerator[None]:
                assert isinstance(event, events.Start)
                yield commands.OpenConnection(self.context.server)
                self.state = self.state_bar

            state = state_foo

            def state_bar(self, event: events.Event) -> layer.CommandGenerator[None]:
                assert isinstance(event, events.DataReceived)
                yield commands.Log("baz", "info")

        tlayer = TLayer(tctx)
        assert (
                tutils.Playbook(tlayer, hooks=True, logs=True)
                << commands.Log(" >> Start({})", "debug")
                << commands.Log(" << OpenConnection({'connection': Server({'id': '…rverid', 'address': None, "
                                "'state': <ConnectionState.CLOSED: 0>})})",
                                "debug")
                << commands.OpenConnection(tctx.server)
                >> events.DataReceived(tctx.client, b"foo")
                << commands.Log(" >! DataReceived(client, b'foo')", "debug")
                >> tutils.reply(None, to=-3)
                << commands.Log(" >> Reply(OpenConnection({'connection': Server("
                                "{'id': '…rverid', 'address': None, 'state': <ConnectionState.OPEN: 3>, "
                                "'timestamp_start': 1624544785})}), None)", "debug")
                << commands.Log(" !> DataReceived(client, b'foo')", "debug")

                << commands.Log("baz", "info")
        )
        assert repr(tlayer) == "TLayer(state: bar)"

    def test_debug_shorten(self, tctx):
        t = layer.Layer(tctx)
        t.debug = "  "
        assert t._Layer__debug("x" * 600).message == "  " + "x" * 512 + "…"
        assert t._Layer__debug("x" * 600).message == "  " + "x" * 256 + "…"
        assert t._Layer__debug("foo").message == "  foo"


class TestNextLayer:
    def test_simple(self, tctx: Context):
        nl = layer.NextLayer(tctx, ask_on_start=True)
        nl.debug = "  "
        playbook = tutils.Playbook(nl, hooks=True)

        assert (
                playbook
                << layer.NextLayerHook(nl)
                >> tutils.reply()
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

    def test_late_hook_reply(self, tctx: Context):
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
    def test_receive_close(self, tctx: Context, layer_found: bool):
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

    def test_func_references(self, tctx: Context):
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

    def test_repr(self, tctx: Context):
        nl = layer.NextLayer(tctx)
        nl.layer = tutils.EchoLayer(tctx)
        assert repr(nl)
        assert nl.stack_pos
        assert nl.layer.stack_pos
