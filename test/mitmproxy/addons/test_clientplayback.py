import asyncio
import ssl
from contextlib import asynccontextmanager

import pytest
import wsproto
import wsproto.events
from wsproto.frame_protocol import Opcode

from mitmproxy.addons.clientplayback import ClientPlayback
from mitmproxy.addons.clientplayback import ReplayHandler
from mitmproxy.addons.proxyserver import Proxyserver
from mitmproxy.addons.tlsconfig import TlsConfig
from mitmproxy.connection import Address
from mitmproxy.exceptions import CommandError
from mitmproxy.exceptions import OptionsError
from mitmproxy.options import Options
from mitmproxy.test import taddons
from mitmproxy.test import tflow
from mitmproxy.websocket import WebSocketMessage


async def _ws_upgrade(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    await reader.readuntil(b"\r\n\r\n")
    writer.write(
        b"HTTP/1.1 101 Switching Protocols\r\n"
        b"Upgrade: websocket\r\n"
        b"Connection: Upgrade\r\n"
        b"\r\n"
    )
    await writer.drain()
    return wsproto.Connection(wsproto.ConnectionType.SERVER)


def _ws_payload(ev: wsproto.events.Event) -> bytes | None:
    if isinstance(ev, wsproto.events.BytesMessage) and ev.message_finished:
        return ev.data
    if isinstance(ev, wsproto.events.TextMessage) and ev.message_finished:
        return ev.data.encode()
    return None


def _ws_send_close(ws: wsproto.Connection, code: int = 1000, reason: str = "") -> bytes:
    return ws.send(wsproto.events.CloseConnection(code, reason))


@asynccontextmanager
async def tcp_server(handle_conn, **server_args) -> Address:
    """TCP server context manager that...

    1. Exits only after all handlers have returned.
    2. Ensures that all handlers are closed properly. If we don't do that,
       we get ghost errors in others tests from StreamWriter.__del__.

    Spawning a TCP server is relatively slow. Consider using in-memory networking for faster tests.
    """
    if not hasattr(asyncio, "TaskGroup"):
        pytest.skip("Skipped because asyncio.TaskGroup is unavailable.")

    tasks = asyncio.TaskGroup()

    async def handle_conn_wrapper(
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        try:
            await handle_conn(reader, writer)
        except Exception as e:
            print(f"!!! TCP handler failed: {e}")
            raise
        finally:
            if not writer.is_closing():
                writer.close()
            await writer.wait_closed()

    async def _handle(r, w):
        tasks.create_task(handle_conn_wrapper(r, w))

    server = await asyncio.start_server(_handle, "127.0.0.1", 0, **server_args)
    await server.start_serving()
    async with server:
        async with tasks:
            yield server.sockets[0].getsockname()


@pytest.mark.parametrize("mode", ["http", "https", "upstream", "err"])
@pytest.mark.parametrize("concurrency", [-1, 1])
async def test_playback(tdata, mode, concurrency):
    async def handler(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        if mode == "err":
            return
        req = await reader.readline()
        if mode == "upstream":
            assert req == b"GET http://address:22/path HTTP/1.1\r\n"
        else:
            assert req == b"GET /path HTTP/1.1\r\n"
        req = await reader.readuntil(b"data")
        assert req == (
            b"header: qvalue\r\n"
            b"content-length: 4\r\nHost: example.mitmproxy.org\r\n\r\n"
            b"data"
        )
        writer.write(b"HTTP/1.1 204 No Content\r\n\r\n")
        await writer.drain()
        assert not await reader.read()

    cp = ClientPlayback()
    ps = Proxyserver()
    tls = TlsConfig()
    with taddons.context(cp, ps, tls) as tctx:
        tctx.configure(cp, client_replay_concurrency=concurrency)

        server_args = {}
        if mode == "https":
            server_args["ssl"] = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            server_args["ssl"].load_cert_chain(
                certfile=tdata.path(
                    "mitmproxy/net/data/verificationcerts/trusted-leaf.crt"
                ),
                keyfile=tdata.path(
                    "mitmproxy/net/data/verificationcerts/trusted-leaf.key"
                ),
            )
            tctx.configure(
                tls,
                ssl_verify_upstream_trusted_ca=tdata.path(
                    "mitmproxy/net/data/verificationcerts/trusted-root.crt"
                ),
            )

        async with tcp_server(handler, **server_args) as addr:
            cp.running()
            flow = tflow.tflow(live=False)
            flow.request.content = b"data"
            if mode == "upstream":
                tctx.options.mode = [f"upstream:http://{addr[0]}:{addr[1]}"]
                flow.request.authority = f"{addr[0]}:{addr[1]}"
                flow.request.host, flow.request.port = "address", 22
            else:
                flow.request.host, flow.request.port = addr
            if mode == "https":
                flow.request.scheme = "https"
            # Used for SNI
            flow.request.host_header = "example.mitmproxy.org"
            cp.start_replay([flow])
            assert cp.count() == 1
            await asyncio.wait_for(cp.queue.join(), 5)
            while cp.replay_tasks:
                await asyncio.sleep(0.001)
        if mode != "err":
            assert flow.response.status_code == 204
        await cp.done()


async def test_playback_https_upstream():
    async def handler(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        conn_req = await reader.readuntil(b"\r\n\r\n")
        assert conn_req == b"CONNECT address:22 HTTP/1.1\r\nHost: address:22\r\n\r\n"
        writer.write(b"HTTP/1.1 502 Bad Gateway\r\n\r\n")
        await writer.drain()
        assert not await reader.read()

    cp = ClientPlayback()
    ps = Proxyserver()
    with taddons.context(cp, ps) as tctx:
        tctx.configure(cp)
        async with tcp_server(handler) as addr:
            cp.running()
            flow = tflow.tflow(live=False)
            flow.request.scheme = b"https"
            flow.request.content = b"data"
            tctx.options.mode = [f"upstream:http://{addr[0]}:{addr[1]}"]
            cp.start_replay([flow])
            assert cp.count() == 1
            await asyncio.wait_for(cp.queue.join(), 5)

        assert flow.response is None
        assert (
            str(flow.error)
            == f"Upstream proxy {addr[0]}:{addr[1]} refused HTTP CONNECT request: 502 Bad Gateway"
        )
        await cp.done()


async def test_playback_crash(monkeypatch, caplog_async):
    async def raise_err(*_, **__):
        raise ValueError("oops")

    monkeypatch.setattr(ReplayHandler, "replay", raise_err)
    cp = ClientPlayback()
    with taddons.context(cp):
        cp.running()
        cp.start_replay([tflow.tflow(live=False)])
        await caplog_async.await_log("Client replay has crashed!")
        assert "oops" in caplog_async.caplog.text
        assert cp.count() == 0
        await cp.done()


def test_check():
    cp = ClientPlayback()
    f = tflow.tflow(resp=True)
    f.live = True
    assert "live flow" in cp.check(f)

    f = tflow.tflow(resp=True, live=False)
    f.intercepted = True
    assert "intercepted flow" in cp.check(f)

    f = tflow.tflow(resp=True, live=False)
    f.request = None
    assert "missing request" in cp.check(f)

    f = tflow.tflow(resp=True, live=False)
    f.request.raw_content = None
    assert "missing content" in cp.check(f)

    for f in (tflow.ttcpflow(), tflow.tudpflow()):
        f.live = False
        assert "Can only replay HTTP" in cp.check(f)

    f = tflow.twebsocketflow()
    f.live = False
    assert cp.check(f) is None


def test_replay_handler_preserves_websocket_messages():
    flow = tflow.twebsocketflow()
    flow.live = False
    recorded = list(flow.websocket.messages)
    handler = ReplayHandler(flow, Options())
    assert handler.recorded_websocket_messages == recorded
    assert handler.recorded_closed_by_client is False
    assert handler.recorded_close_code == 1000
    assert flow.websocket is None


async def test_finish_is_idempotent():
    flow = tflow.tflow(live=False)
    handler = ReplayHandler(flow, Options())
    await handler._finish()
    await handler._finish()
    await handler._send_next_client_burst()
    await handler._finish_websocket_replay()
    assert handler.done.is_set()


async def test_playback_websocket():
    received: list[bytes] = []

    async def handler(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        ws = await _ws_upgrade(reader, writer)
        while True:
            data = await reader.read(65536)
            if not data:
                break
            ws.receive_data(data)
            for ev in ws.events():
                payload = _ws_payload(ev)
                if payload is not None:
                    received.append(payload)
                    if len(received) == 2:
                        writer.write(ws.send(wsproto.events.TextMessage("it's me")))
                        writer.write(_ws_send_close(ws, 1000, "Close Reason"))
                        await writer.drain()

    cp = ClientPlayback()
    ps = Proxyserver()
    with taddons.context(cp, ps):
        async with tcp_server(handler) as addr:
            cp.running()
            flow = tflow.twebsocketflow()
            flow.live = False
            flow.websocket.messages.insert(
                0, WebSocketMessage(Opcode.TEXT, True, b"dropped", dropped=True)
            )
            flow.websocket.messages.append(
                WebSocketMessage(Opcode.TEXT, True, b"dropped-end", dropped=True)
            )
            flow.request.host, flow.request.port = addr
            cp.start_replay([flow])
            assert cp.count() == 1
            await asyncio.wait_for(cp.queue.join(), 5)
            while cp.replay_tasks:
                await asyncio.sleep(0.001)
        assert flow.response.status_code == 101
        assert received == [b"hello binary", b"hello text"]
        assert [m.content for m in flow.websocket.messages] == [
            b"hello binary",
            b"hello text",
            b"it's me",
        ]
        assert [m.type for m in flow.websocket.messages] == [
            Opcode.BINARY,
            Opcode.TEXT,
            Opcode.TEXT,
        ]
        assert flow.websocket.closed_by_client is False
        assert flow.websocket.close_code == 1000
        await cp.done()


async def test_playback_websocket_waits_for_server_reply():
    received: list[bytes] = []

    async def read_message(
        reader: asyncio.StreamReader, ws: wsproto.Connection
    ) -> bytes | None:
        while True:
            data = await reader.read(65536)
            if not data:
                return None
            ws.receive_data(data)
            for ev in ws.events():
                payload = _ws_payload(ev)
                if payload is not None:
                    return payload

    async def handler(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        ws = await _ws_upgrade(reader, writer)
        first = await read_message(reader, ws)
        received.append(first)
        try:
            extra = await asyncio.wait_for(reader.read(65536), 0.1)
        except TimeoutError:
            extra = b""
        assert extra == b""
        writer.write(ws.send(wsproto.events.TextMessage("pong1")))
        await writer.drain()
        second = await read_message(reader, ws)
        received.append(second)
        writer.write(ws.send(wsproto.events.TextMessage("pong2")))
        writer.write(_ws_send_close(ws))
        await writer.drain()
        while await reader.read(65536):
            pass

    cp = ClientPlayback()
    ps = Proxyserver()
    with taddons.context(cp, ps):
        async with tcp_server(handler) as addr:
            cp.running()
            flow = tflow.twebsocketflow()
            flow.live = False
            flow.websocket.messages = [
                WebSocketMessage(Opcode.TEXT, True, b"ping1"),
                WebSocketMessage(Opcode.TEXT, False, b"pong1"),
                WebSocketMessage(Opcode.TEXT, True, b"ping2"),
                WebSocketMessage(Opcode.TEXT, False, b"pong2"),
            ]
            flow.request.host, flow.request.port = addr
            cp.start_replay([flow])
            await asyncio.wait_for(cp.queue.join(), 5)
        assert received == [b"ping1", b"ping2"]
        assert [m.content for m in flow.websocket.messages] == [
            b"ping1",
            b"pong1",
            b"ping2",
            b"pong2",
        ]
        await cp.done()


async def test_playback_websocket_binary_and_client_close():
    received: list[bytes] = []
    close: list[wsproto.events.CloseConnection] = []

    async def handler(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        ws = await _ws_upgrade(reader, writer)
        while True:
            data = await reader.read(65536)
            if not data:
                break
            ws.receive_data(data)
            for ev in ws.events():
                if isinstance(ev, wsproto.events.BytesMessage) and ev.message_finished:
                    received.append(ev.data)
                    writer.write(ws.send(wsproto.events.BytesMessage(b"\x02\x03")))
                    await writer.drain()
                elif isinstance(ev, wsproto.events.CloseConnection):
                    close.append(ev)
                    writer.write(ws.send(ev.response()))
                    await writer.drain()
                    return

    cp = ClientPlayback()
    ps = Proxyserver()
    with taddons.context(cp, ps):
        async with tcp_server(handler) as addr:
            cp.running()
            flow = tflow.twebsocketflow()
            flow.live = False
            flow.websocket.messages = [
                WebSocketMessage(Opcode.BINARY, True, b"\x00\x01"),
                WebSocketMessage(Opcode.BINARY, False, b"\x02\x03"),
            ]
            flow.websocket.closed_by_client = True
            flow.websocket.close_code = 1001
            flow.websocket.close_reason = "going away"
            flow.request.host, flow.request.port = addr
            cp.start_replay([flow])
            await asyncio.wait_for(cp.queue.join(), 5)
        assert received == [b"\x00\x01"]
        assert close[0].code == 1001
        assert close[0].reason == "going away"
        assert [m.type for m in flow.websocket.messages] == [
            Opcode.BINARY,
            Opcode.BINARY,
        ]
        assert flow.websocket.closed_by_client is True
        assert flow.websocket.close_code == 1001
        await cp.done()


async def test_playback_websocket_client_abnormal_close():
    async def handler(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        await _ws_upgrade(reader, writer)
        while await reader.read(65536):
            pass

    cp = ClientPlayback()
    ps = Proxyserver()
    with taddons.context(cp, ps):
        async with tcp_server(handler) as addr:
            cp.running()
            flow = tflow.twebsocketflow()
            flow.live = False
            flow.websocket.messages = []
            flow.websocket.closed_by_client = True
            flow.websocket.close_code = 1006
            flow.request.host, flow.request.port = addr
            cp.start_replay([flow])
            await asyncio.wait_for(cp.queue.join(), 5)
        assert flow.response.status_code == 101
        assert flow.websocket.close_code == 1006
        await cp.done()


async def test_playback_websocket_failed_upgrade():
    async def handler(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        await reader.readuntil(b"\r\n\r\n")
        writer.write(b"HTTP/1.1 400 Bad Request\r\nContent-Length: 0\r\n\r\n")
        await writer.drain()
        assert not await reader.read()

    cp = ClientPlayback()
    ps = Proxyserver()
    with taddons.context(cp, ps):
        async with tcp_server(handler) as addr:
            cp.running()
            flow = tflow.twebsocketflow()
            flow.live = False
            flow.request.host, flow.request.port = addr
            cp.start_replay([flow])
            await asyncio.wait_for(cp.queue.join(), 5)
        assert flow.response.status_code == 400
        assert flow.websocket is None
        await cp.done()


async def test_playback_websocket_incomplete_upgrade():
    async def handler(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        return

    cp = ClientPlayback()
    ps = Proxyserver()
    with taddons.context(cp, ps):
        async with tcp_server(handler) as addr:
            cp.running()
            flow = tflow.twebsocketflow()
            flow.live = False
            flow.request.host, flow.request.port = addr
            cp.start_replay([flow])
            await asyncio.wait_for(cp.queue.join(), 5)
        assert flow.response is None
        assert flow.error
        await cp.done()


async def test_start_stop(caplog):
    cp = ClientPlayback()
    with taddons.context(cp):
        cp.start_replay([tflow.tflow(live=False)])
        assert cp.count() == 1

        ws_flow = tflow.twebsocketflow()
        ws_flow.live = False
        cp.start_replay([ws_flow])
        assert cp.count() == 2

        live = tflow.tflow()
        live.live = True
        cp.start_replay([live])
        assert "Can't replay live flow." in caplog.text
        assert cp.count() == 2

        cp.stop_replay()
        assert cp.count() == 0


def test_load(tdata):
    cp = ClientPlayback()
    with taddons.context(cp):
        cp.load_file(tdata.path("mitmproxy/data/dumpfile-018.mitm"))
        assert cp.count() == 1

        with pytest.raises(CommandError):
            cp.load_file("/nonexistent")
        assert cp.count() == 1


def test_configure(tdata):
    cp = ClientPlayback()
    with taddons.context(cp) as tctx:
        assert cp.count() == 0
        tctx.configure(
            cp, client_replay=[tdata.path("mitmproxy/data/dumpfile-018.mitm")]
        )
        assert cp.count() == 1
        tctx.configure(cp, client_replay=[])
        with pytest.raises(OptionsError):
            tctx.configure(cp, client_replay=["nonexistent"])
        tctx.configure(cp, client_replay_concurrency=-1)
        with pytest.raises(OptionsError):
            tctx.configure(cp, client_replay_concurrency=-2)
