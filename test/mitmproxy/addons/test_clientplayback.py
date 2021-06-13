import asyncio
from contextlib import asynccontextmanager

import pytest

from mitmproxy.addons.clientplayback import ClientPlayback, ReplayHandler
from mitmproxy.addons.proxyserver import Proxyserver
from mitmproxy.exceptions import CommandError, OptionsError
from mitmproxy.connection import Address
from mitmproxy.test import taddons, tflow


@asynccontextmanager
async def tcp_server(handle_conn) -> Address:
    server = await asyncio.start_server(handle_conn, '127.0.0.1', 0)
    await server.start_serving()
    try:
        yield server.sockets[0].getsockname()
    finally:
        server.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["regular", "upstream", "err"])
async def test_playback(mode):
    handler_ok = asyncio.Event()

    async def handler(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        if mode == "err":
            writer.close()
            handler_ok.set()
            return
        if mode == "upstream":
            conn_req = await reader.readuntil(b"\r\n\r\n")
            assert conn_req == b'CONNECT address:22 HTTP/1.1\r\n\r\n'
            writer.write(b"HTTP/1.1 200 Connection Established\r\n\r\n")
        req = await reader.readuntil(b"data")
        assert req == (
            b'GET /path HTTP/1.1\r\n'
            b'header: qvalue\r\n'
            b'content-length: 4\r\n'
            b'\r\n'
            b'data'
        )
        writer.write(b"HTTP/1.1 204 No Content\r\n\r\n")
        await writer.drain()
        assert not await reader.read()
        handler_ok.set()

    cp = ClientPlayback()
    ps = Proxyserver()
    with taddons.context(cp, ps) as tctx:
        async with tcp_server(handler) as addr:

            cp.running()
            flow = tflow.tflow()
            flow.request.content = b"data"
            if mode == "upstream":
                tctx.options.mode = f"upstream:http://{addr[0]}:{addr[1]}"
            else:
                flow.request.host, flow.request.port = addr
            cp.start_replay([flow])
            assert cp.count() == 1
            await asyncio.wait_for(cp.queue.join(), 5)
            await asyncio.wait_for(handler_ok.wait(), 5)
            cp.done()
            if mode != "err":
                assert flow.response.status_code == 204


@pytest.mark.asyncio
async def test_playback_crash(monkeypatch):
    async def raise_err():
        raise ValueError("oops")

    monkeypatch.setattr(ReplayHandler, "replay", raise_err)
    cp = ClientPlayback()
    with taddons.context(cp) as tctx:
        cp.running()
        cp.start_replay([tflow.tflow()])
        await tctx.master.await_log("Client replay has crashed!", level="error")
        assert cp.count() == 0
        cp.done()


def test_check():
    cp = ClientPlayback()
    f = tflow.tflow(resp=True)
    f.live = True
    assert "live flow" in cp.check(f)

    f = tflow.tflow(resp=True)
    f.intercepted = True
    assert "intercepted flow" in cp.check(f)

    f = tflow.tflow(resp=True)
    f.request = None
    assert "missing request" in cp.check(f)

    f = tflow.tflow(resp=True)
    f.request.raw_content = None
    assert "missing content" in cp.check(f)

    f = tflow.ttcpflow()
    assert "Can only replay HTTP" in cp.check(f)


@pytest.mark.asyncio
async def test_start_stop(tdata):
    cp = ClientPlayback()
    with taddons.context(cp) as tctx:
        cp.start_replay([tflow.tflow()])
        assert cp.count() == 1

        cp.start_replay([tflow.twebsocketflow()])
        await tctx.master.await_log("Can't replay WebSocket flows.", level="warn")
        assert cp.count() == 1

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
        tctx.configure(cp, client_replay=[tdata.path("mitmproxy/data/dumpfile-018.mitm")])
        assert cp.count() == 1
        tctx.configure(cp, client_replay=[])
        with pytest.raises(OptionsError):
            tctx.configure(cp, client_replay=["nonexistent"])
