import asyncio
from contextlib import asynccontextmanager

import pytest

from mitmproxy.addons.proxyserver import Proxyserver
from mitmproxy.proxy.layers.http import HTTPMode
from mitmproxy.proxy import layers
from mitmproxy.connection import Address
from mitmproxy.test import taddons


class HelperAddon:
    def __init__(self):
        self.flows = []
        self.layers = [
            lambda ctx: layers.modes.HttpProxy(ctx),
            lambda ctx: layers.HttpLayer(ctx, HTTPMode.regular)
        ]

    def request(self, f):
        self.flows.append(f)

    def next_layer(self, nl):
        nl.layer = self.layers.pop(0)(nl.context)


@asynccontextmanager
async def tcp_server(handle_conn) -> Address:
    server = await asyncio.start_server(handle_conn, '127.0.0.1', 0)
    await server.start_serving()
    try:
        yield server.sockets[0].getsockname()
    finally:
        server.close()


@pytest.mark.asyncio
async def test_start_stop():
    async def server_handler(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        assert await reader.readuntil(b"\r\n\r\n") == b"GET /hello HTTP/1.1\r\n\r\n"
        writer.write(b"HTTP/1.1 204 No Content\r\n\r\n")
        await writer.drain()
        writer.close()

    ps = Proxyserver()
    with taddons.context(ps) as tctx:
        state = HelperAddon()
        tctx.master.addons.add(state)
        async with tcp_server(server_handler) as addr:
            tctx.configure(ps, listen_host="127.0.0.1", listen_port=0)
            assert not ps.server
            ps.running()
            await tctx.master.await_log("Proxy server listening", level="info")
            assert ps.server

            proxy_addr = ps.server.sockets[0].getsockname()[:2]
            reader, writer = await asyncio.open_connection(*proxy_addr)
            req = f"GET http://{addr[0]}:{addr[1]}/hello HTTP/1.1\r\n\r\n"
            writer.write(req.encode())
            assert await reader.readuntil(b"\r\n\r\n") == b"HTTP/1.1 204 No Content\r\n\r\n"

            tctx.configure(ps, server=False)
            await tctx.master.await_log("Stopping server", level="info")
            assert not ps.server
            assert state.flows
            assert state.flows[0].request.path == "/hello"
            assert state.flows[0].response.status_code == 204


@pytest.mark.asyncio
async def test_warn_no_nextlayer():
    """
    Test that we log an error if the proxy server is started without NextLayer addon.
    That is a mean trap to fall into when writing end-to-end tests.
    """
    ps = Proxyserver()
    with taddons.context(ps) as tctx:
        tctx.configure(ps, listen_host="127.0.0.1", listen_port=0)
        ps.running()
        await tctx.master.await_log("Proxy server listening at", level="info")
        assert tctx.master.has_log("Warning: Running proxyserver without nextlayer addon!", level="warn")
        await ps.shutdown_server()
