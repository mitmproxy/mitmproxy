import asyncio
from contextlib import asynccontextmanager

import pytest

from mitmproxy import exceptions
from mitmproxy.addons.proxyserver import Proxyserver
from mitmproxy.connection import Address
from mitmproxy.proxy import layers, server_hooks
from mitmproxy.proxy.layers.http import HTTPMode
from mitmproxy.test import taddons, tflow
from mitmproxy.test.tflow import tclient_conn, tserver_conn


class HelperAddon:
    def __init__(self):
        self.flows = []
        self.layers = [
            lambda ctx: layers.modes.HttpProxy(ctx),
            lambda ctx: layers.HttpLayer(ctx, HTTPMode.regular),
            lambda ctx: layers.TCPLayer(ctx),
        ]

    def request(self, f):
        self.flows.append(f)

    def tcp_start(self, f):
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
            assert repr(ps) == "ProxyServer(running, 1 active conns)"

            tctx.configure(ps, server=False)
            await tctx.master.await_log("Stopping server", level="info")
            assert not ps.server
            assert state.flows
            assert state.flows[0].request.path == "/hello"
            assert state.flows[0].response.status_code == 204

            # Waiting here until everything is really torn down... takes some effort.
            conn_handler = list(ps._connections.values())[0]
            client_handler = conn_handler.transports[conn_handler.client].handler
            writer.close()
            await writer.wait_closed()
            try:
                await client_handler
            except asyncio.CancelledError:
                pass
            for _ in range(5):
                # Get all other scheduled coroutines to run.
                await asyncio.sleep(0)
            assert repr(ps) == "ProxyServer(stopped, 0 active conns)"


@pytest.mark.asyncio
async def test_inject() -> None:
    async def server_handler(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        while s := await reader.read(1):
            writer.write(s.upper())

    ps = Proxyserver()
    with taddons.context(ps) as tctx:
        state = HelperAddon()
        tctx.master.addons.add(state)
        async with tcp_server(server_handler) as addr:
            tctx.configure(ps, listen_host="127.0.0.1", listen_port=0)
            ps.running()
            await tctx.master.await_log("Proxy server listening", level="info")
            proxy_addr = ps.server.sockets[0].getsockname()[:2]
            reader, writer = await asyncio.open_connection(*proxy_addr)

            req = f"CONNECT {addr[0]}:{addr[1]} HTTP/1.1\r\n\r\n"
            writer.write(req.encode())
            assert await reader.readuntil(b"\r\n\r\n") == b"HTTP/1.1 200 Connection established\r\n\r\n"

            writer.write(b"a")
            assert await reader.read(1) == b"A"
            ps.inject_tcp(state.flows[0], False, b"b")
            assert await reader.read(1) == b"B"
            ps.inject_tcp(state.flows[0], True, b"c")
            assert await reader.read(1) == b"c"


@pytest.mark.asyncio
async def test_inject_fail() -> None:
    ps = Proxyserver()
    with taddons.context(ps) as tctx:
        ps.inject_websocket(
            tflow.tflow(),
            True,
            b"test"
        )
        await tctx.master.await_log("Cannot inject WebSocket messages into non-WebSocket flows.", level="warn")
        ps.inject_tcp(
            tflow.tflow(),
            True,
            b"test"
        )
        await tctx.master.await_log("Cannot inject TCP messages into non-TCP flows.", level="warn")

        ps.inject_websocket(
            tflow.twebsocketflow(),
            True,
            b"test"
        )
        await tctx.master.await_log("Flow is not from a live connection.", level="warn")
        ps.inject_websocket(
            tflow.ttcpflow(),
            True,
            b"test"
        )
        await tctx.master.await_log("Flow is not from a live connection.", level="warn")


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


def test_self_connect():
    server = tserver_conn()
    client = tclient_conn()
    server.address = ("localhost", 8080)
    ps = Proxyserver()
    with taddons.context(ps) as tctx:
        # not calling .running() here to avoid unnecessary socket
        ps.options = tctx.options
        ps.server_connect(
            server_hooks.ServerConnectionHookData(server, client)
        )
        assert server.error == "Stopped mitmproxy from recursively connecting to itself."


def test_options():
    ps = Proxyserver()
    with taddons.context(ps) as tctx:
        with pytest.raises(exceptions.OptionsError):
            tctx.configure(ps, body_size_limit="invalid")
        tctx.configure(ps, body_size_limit="1m")

        with pytest.raises(exceptions.OptionsError):
            tctx.configure(ps, stream_large_bodies="invalid")
        tctx.configure(ps, stream_large_bodies="1m")
