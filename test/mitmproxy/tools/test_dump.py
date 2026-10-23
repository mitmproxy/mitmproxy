import asyncio
import json
import weakref
from io import StringIO

import pytest

from mitmproxy import exceptions
from mitmproxy import hooks
from mitmproxy import io
from mitmproxy import options
from mitmproxy import websocket
from mitmproxy.proxy import commands
from mitmproxy.proxy import context
from mitmproxy.proxy import events
from mitmproxy.proxy.layers import http
from mitmproxy.proxy.layers import websocket as websocket_layer
from mitmproxy.test import tflow
from mitmproxy.tools import dump


@pytest.fixture
async def dump_master(tmp_path, caplog):
    m = dump.DumpMaster(options.Options(confdir=str(tmp_path)), with_termlog=False)
    m.addons.get("dumper").outfp = StringIO()
    m.options.update(flow_detail=0)
    try:
        yield m
    finally:
        await m.done()
        assert not any(
            "Addon error:" in record.getMessage()
            for record in caplog.get_records("call") + caplog.get_records("teardown")
        )


async def handle_event(master, layer, event):
    """Run real addon hooks between protocol-layer commands."""
    output = []
    for command in layer.handle_event(event):
        if isinstance(command, commands.StartHook):
            await master.addons.handle_lifecycle(command)
            output.extend(
                await handle_event(master, layer, events.HookCompleted(command))
            )
        else:
            output.append(command)
    return output


async def start_websocket(master):
    f = tflow.twebsocketflow()
    f.websocket = websocket.WebSocketData()
    ctx = context.Context(f.client_conn, master.options)
    ctx.server = f.server_conn
    layer = websocket_layer.WebsocketLayer(ctx, f)
    await master.addons.handle_lifecycle(http.HttpRequestHook(f))
    await master.addons.handle_lifecycle(http.HttpResponseHook(f))
    await handle_event(master, layer, events.Start())
    return layer


class TestDumpMaster:
    @pytest.mark.parametrize("termlog", [False, True])
    async def test_addons_termlog(self, capsys, termlog):
        o = options.Options()
        m = dump.DumpMaster(o, with_termlog=termlog)
        assert (m.addons.get("termlog") is not None) == termlog
        await m.done()

    @pytest.mark.parametrize("dumper", [False, True])
    async def test_addons_dumper(self, capsys, dumper):
        o = options.Options()
        m = dump.DumpMaster(o, with_dumper=dumper, with_termlog=False)
        assert (m.addons.get("dumper") is not None) == dumper
        await m.done()

    @pytest.mark.parametrize("flow_detail", [0, 1, 3])
    async def test_websocket_history_default(self, dump_master, flow_detail):
        dump_master.options.update(flow_detail=flow_detail)
        seen = []

        class ObserveMessages:
            def websocket_message(self, flow):
                seen.append(weakref.ref(flow.websocket.messages[-1]))

        dump_master.addons.add(ObserveMessages())
        layer = await start_websocket(dump_master)
        for _ in range(32):
            output = await handle_event(
                dump_master,
                layer,
                events.DataReceived(layer.context.server, b"\x82\x03foo"),
            )
            assert len(output) == 1
            assert isinstance(output[0], commands.SendData)
            assert output[0].data == b"\x82\x03foo"
            assert layer.flow.websocket.messages == []
            assert seen[-1]() is None

        assert len(seen) == 32
        output = dump_master.addons.get("dumper").outfp.getvalue()
        assert output.count("WebSocket binary message") == (32 if flow_detail else 0)

    @pytest.mark.parametrize("drop", [False, True])
    async def test_websocket_hooks(self, dump_master, drop):
        seen = []

        class ModifyMessage:
            async def websocket_message(self, flow):
                message = flow.websocket.messages[-1]
                message.content = b"bar"
                seen.append(weakref.ref(message))
                await asyncio.sleep(0)

        class LaterHook:
            def websocket_message(self, flow):
                message = flow.websocket.messages[-1]
                assert message is seen[-1]()
                assert message.content == b"bar"
                if drop:
                    message.drop()

        dump_master.addons.add(ModifyMessage(), LaterHook())
        layer = await start_websocket(dump_master)
        output = await handle_event(
            dump_master,
            layer,
            events.DataReceived(layer.context.server, b"\x81\x03foo"),
        )
        assert [cmd.data for cmd in output] == ([] if drop else [b"\x81\x03bar"])
        assert layer.flow.websocket.messages == []
        assert seen[0]() is None

    @pytest.mark.parametrize(
        "consumer",
        ["save_stream_file", "hardump", "keep_websocket_messages", "dumper_filter"],
    )
    async def test_websocket_history_consumers(self, dump_master, tmp_path, consumer):
        path = tmp_path / "capture"
        value = {
            "save_stream_file": str(path),
            "hardump": str(path),
            "keep_websocket_messages": True,
            "dumper_filter": "~b foo",
        }[consumer]
        dump_master.options.update(**{consumer: value}, flow_detail=1)
        # Match an earlier message at connection end, not just the final message.
        dump_master.options.update(save_stream_filter="~b foo")
        layer = await start_websocket(dump_master)
        for payload in [b"foo", b"bar"]:
            await handle_event(
                dump_master,
                layer,
                events.DataReceived(layer.context.server, b"\x81\x03" + payload),
            )
        await handle_event(
            dump_master, layer, events.ConnectionClosed(layer.context.server)
        )
        assert [m.content for m in layer.flow.websocket.messages] == [b"foo", b"bar"]

        if consumer == "save_stream_file":
            with path.open("rb") as f:
                saved = list(io.FlowReader(f).stream())
            assert len(saved) == 1
            assert saved[0].websocket.get_state() == layer.flow.websocket.get_state()
        elif consumer == "hardump":
            dump_master.addons.get("savehar").done()
            messages = json.loads(path.read_text())["log"]["entries"][0][
                "_webSocketMessages"
            ]
            assert [m["data"] for m in messages] == ["foo", "bar"]
        elif consumer == "dumper_filter":
            output = dump_master.addons.get("dumper").outfp.getvalue()
            assert output.count("WebSocket text message") == 2

    async def test_websocket_addon_requests_history(self, dump_master):
        lengths = []

        class NeedsHistory:
            def websocket_start(self, flow):
                flow.websocket.store_messages = True

            def websocket_message(self, flow):
                lengths.append(len(flow.websocket.messages))

        dump_master.addons.add(NeedsHistory())
        layer = await start_websocket(dump_master)
        for _ in range(2):
            await handle_event(
                dump_master,
                layer,
                events.DataReceived(layer.context.server, b"\x81\x03foo"),
            )
        assert lengths == [1, 2]

    @pytest.mark.parametrize(
        "consumer",
        ["save_stream_file", "hardump", "keep_websocket_messages", "dumper_filter"],
    )
    async def test_websocket_history_option_change(
        self, dump_master, tmp_path, consumer
    ):
        layer = await start_websocket(dump_master)
        await handle_event(
            dump_master,
            layer,
            events.DataReceived(layer.context.server, b"\x81\x03foo"),
        )
        path = tmp_path / "capture"
        path.write_bytes(b"existing capture")
        value = {
            "save_stream_file": str(path),
            "hardump": str(path),
            "keep_websocket_messages": True,
            "dumper_filter": "~b foo",
        }[consumer]
        previous = getattr(dump_master.options, consumer)
        with pytest.raises(exceptions.OptionsError, match="Close these connections"):
            dump_master.options.update(**{consumer: value})
        assert getattr(dump_master.options, consumer) == previous
        assert path.read_bytes() == b"existing capture"

        # Unrelated option changes remain possible while forwarding.
        dump_master.options.update(flow_detail=2)
        await handle_event(
            dump_master, layer, events.ConnectionClosed(layer.context.server)
        )
        dump_master.options.update(**{consumer: value})
        new_layer = await start_websocket(dump_master)
        assert new_layer.flow.websocket.store_messages

    @pytest.mark.parametrize("nested_update", [False, True])
    async def test_websocket_recording_during_end_hook(
        self, dump_master, tmp_path, nested_update
    ):
        errors = []

        class EnableRecording:
            def websocket_end(self, flow):
                if nested_update:
                    dump_master.addons.trigger(hooks.UpdateHook([flow]))
                try:
                    dump_master.options.update(
                        save_stream_file=str(tmp_path / "capture")
                    )
                except exceptions.OptionsError as e:
                    errors.append(str(e))

        # Run before Save, as script addons do.
        dump_master.addons.get("scriptloader").addons.append(EnableRecording())
        layer = await start_websocket(dump_master)
        await handle_event(
            dump_master,
            layer,
            events.DataReceived(layer.context.server, b"\x81\x03foo"),
        )
        await handle_event(
            dump_master, layer, events.ConnectionClosed(layer.context.server)
        )
        assert len(errors) == 1
        assert "Close these connections" in errors[0]
        assert not (tmp_path / "capture").exists()
        dump_master.options.update(save_stream_file=str(tmp_path / "capture"))

    async def test_websocket_read_file(self, dump_master):
        f = tflow.twebsocketflow().copy()
        expected = f.websocket.get_state()
        await dump_master.load_flow(f)
        assert f.websocket.get_state() == expected
        dump_master.options.update(keep_websocket_messages=True)

    async def test_websocket_history_without_dumper(self, tmp_path):
        m = dump.DumpMaster(
            options.Options(confdir=str(tmp_path)),
            with_termlog=False,
            with_dumper=False,
        )
        try:
            layer = await start_websocket(m)
            assert not layer.flow.websocket.store_messages
        finally:
            await m.done()
