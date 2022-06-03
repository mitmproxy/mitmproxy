import asyncio
from contextlib import asynccontextmanager
import socket
from unittest.mock import Mock

import pytest

import mitmproxy.platform
from mitmproxy import dns, exceptions
from mitmproxy.addons import dns_resolver
from mitmproxy.addons.proxyserver import Proxyserver
from mitmproxy.connection import Address
from mitmproxy.net import udp
from mitmproxy.proxy import layers, server_hooks
from mitmproxy.proxy.layers.http import HTTPMode
from mitmproxy.test import taddons, tflow
from mitmproxy.test.tflow import tclient_conn, tserver_conn
from mitmproxy.test.tutils import tdnsreq


class HelperAddon:
    def __init__(self):
        self.flows = []
        self.layers = [
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
    server = await asyncio.start_server(handle_conn, "127.0.0.1", 0)
    await server.start_serving()
    try:
        yield server.sockets[0].getsockname()
    finally:
        server.close()


async def test_start_stop():
    async def server_handler(
        reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ):
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
            assert not ps.servers
            await ps.running()
            await tctx.master.await_log("HTTP(S) proxy listening", level="info")
            assert ps.servers

            proxy_addr = ps.listen_addrs()[0]
            reader, writer = await asyncio.open_connection(*proxy_addr)
            req = f"GET http://{addr[0]}:{addr[1]}/hello HTTP/1.1\r\n\r\n"
            writer.write(req.encode())
            assert (
                await reader.readuntil(b"\r\n\r\n")
                == b"HTTP/1.1 204 No Content\r\n\r\n"
            )
            assert repr(ps) == "Proxyserver(1 active conns)"

            await ps.setup_servers()  # assert this can always be called without side effects
            tctx.configure(ps, server=False)
            await tctx.master.await_log("Stopped regular proxy server.", level="info")
            async with ps._lock:
                pass  # wait until start/stop is finished.
            assert not ps.servers
            assert state.flows
            assert state.flows[0].request.path == "/hello"
            assert state.flows[0].response.status_code == 204

            # Waiting here until everything is really torn down... takes some effort.
            conn_handler = list(ps.connections.values())[0]
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
            assert repr(ps) == "Proxyserver(0 active conns)"


async def test_inject() -> None:
    async def server_handler(
        reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ):
        while s := await reader.read(1):
            writer.write(s.upper())

    ps = Proxyserver()
    with taddons.context(ps) as tctx:
        state = HelperAddon()
        tctx.master.addons.add(state)
        async with tcp_server(server_handler) as addr:
            tctx.configure(ps, listen_host="127.0.0.1", listen_port=0)
            await ps.running()
            await tctx.master.await_log("HTTP(S) proxy listening", level="info")
            proxy_addr = ps.servers["regular"].listen_addrs[0]
            reader, writer = await asyncio.open_connection(*proxy_addr)

            req = f"CONNECT {addr[0]}:{addr[1]} HTTP/1.1\r\n\r\n"
            writer.write(req.encode())
            assert (
                await reader.readuntil(b"\r\n\r\n")
                == b"HTTP/1.1 200 Connection established\r\n\r\n"
            )

            writer.write(b"a")
            assert await reader.read(1) == b"A"
            ps.inject_tcp(state.flows[0], False, b"b")
            assert await reader.read(1) == b"B"
            ps.inject_tcp(state.flows[0], True, b"c")
            assert await reader.read(1) == b"c"


async def test_inject_fail() -> None:
    ps = Proxyserver()
    with taddons.context(ps) as tctx:
        ps.inject_websocket(tflow.tflow(), True, b"test")
        await tctx.master.await_log(
            "Cannot inject WebSocket messages into non-WebSocket flows.", level="warn"
        )
        ps.inject_tcp(tflow.tflow(), True, b"test")
        await tctx.master.await_log(
            "Cannot inject TCP messages into non-TCP flows.", level="warn"
        )

        ps.inject_websocket(tflow.twebsocketflow(), True, b"test")
        await tctx.master.await_log("Flow is not from a live connection.", level="warn")
        ps.inject_websocket(tflow.ttcpflow(), True, b"test")
        await tctx.master.await_log("Flow is not from a live connection.", level="warn")


async def test_warn_no_nextlayer():
    """
    Test that we log an error if the proxy server is started without NextLayer addon.
    That is a mean trap to fall into when writing end-to-end tests.
    """
    ps = Proxyserver()
    with taddons.context(ps) as tctx:
        tctx.configure(ps, listen_host="127.0.0.1", listen_port=0, server=False)
        await ps.running()
        await tctx.master.await_log("Warning: Running proxyserver without nextlayer addon!", level="warn")


async def test_self_connect():
    server = tserver_conn()
    client = tclient_conn()
    server.address = ("localhost", 8080)
    ps = Proxyserver()
    with taddons.context(ps) as tctx:
        tctx.configure(ps, listen_host="127.0.0.1", listen_port=0)
        await ps.running()
        await tctx.master.await_log("HTTP(S) proxy listening", level="info")
        assert ps.servers
        server.address = ("localhost", ps.servers["regular"].listen_addrs[0][1])
        ps.server_connect(server_hooks.ServerConnectionHookData(server, client))
        assert "Request destination unknown" in server.error
        tctx.configure(ps, server=False)


def test_options():
    ps = Proxyserver()
    with taddons.context(ps) as tctx:
        with pytest.raises(exceptions.OptionsError):
            tctx.configure(ps, stream_large_bodies="invalid")
        tctx.configure(ps, stream_large_bodies="1m")

        with pytest.raises(exceptions.OptionsError):
            tctx.configure(ps, body_size_limit="invalid")
        tctx.configure(ps, body_size_limit="1m")

        with pytest.raises(exceptions.OptionsError):
            tctx.configure(ps, connect_addr="invalid")
        tctx.configure(ps, connect_addr="1.2.3.4")
        assert ps._connect_addr == ("1.2.3.4", 0)

        with pytest.raises(exceptions.OptionsError):
            tctx.configure(ps, mode=["invalid!"])
        with pytest.raises(exceptions.OptionsError):
            tctx.configure(ps, mode=["regular", "reverse:example.com"])
        tctx.configure(ps, mode=["regular"], server=False)


async def test_startup_err(monkeypatch) -> None:
    async def _raise(*_):
        raise OSError("cannot bind")

    monkeypatch.setattr(asyncio, "start_server", _raise)

    ps = Proxyserver()
    with taddons.context(ps) as tctx:
        await ps.running()
        await tctx.master.await_log("cannot bind", level="error")


async def test_shutdown_err() -> None:
    async def _raise(*_):
        raise OSError("cannot close")

    ps = Proxyserver()
    with taddons.context(ps) as tctx:
        tctx.configure(ps, listen_host="127.0.0.1", listen_port=0)
        await ps.running()
        assert ps.servers
        for server in ps.servers.values():
            setattr(server, "stop", _raise)
        tctx.configure(ps, server=False)
        await tctx.master.await_log("cannot close", level="error")


class DummyResolver:
    async def dns_request(self, flow: dns.DNSFlow) -> None:
        flow.response = await dns_resolver.resolve_message(flow.request, self)

    async def getaddrinfo(self, host: str, port: int, *, family: int):
        if family == socket.AF_INET and host == "dns.google":
            return [(socket.AF_INET, None, None, None, ("8.8.8.8", port))]
        e = socket.gaierror()
        e.errno = socket.EAI_NONAME
        raise e


async def test_dns() -> None:
    ps = Proxyserver()
    with taddons.context(ps, DummyResolver()) as tctx:
        tctx.configure(
            ps,
            mode=["dns@127.0.0.1:0"],
        )
        await ps.running()
        await tctx.master.await_log("DNS server listening at", level="info")
        assert ps.servers
        dns_addr = ps.servers["dns@127.0.0.1:0"].listen_addrs[0]
        r, w = await udp.open_connection(*dns_addr)
        w.write(b"\x00")
        await tctx.master.await_log("Invalid DNS datagram received", level="info")
        req = tdnsreq()
        w.write(req.packed)
        resp = dns.Message.unpack(await r.read(udp.MAX_DATAGRAM_SIZE))
        assert req.id == resp.id and "8.8.8.8" in str(resp)
        assert len(ps.connections) == 1
        w.write(req.packed)
        resp = dns.Message.unpack(await r.read(udp.MAX_DATAGRAM_SIZE))
        assert req.id == resp.id and "8.8.8.8" in str(resp)
        assert len(ps.connections) == 1
        req.id = req.id + 1
        w.write(req.packed)
        resp = dns.Message.unpack(await r.read(udp.MAX_DATAGRAM_SIZE))
        assert req.id == resp.id and "8.8.8.8" in str(resp)
        assert len(ps.connections) == 2
        tctx.configure(ps, server=False)
        await tctx.master.await_log("Stopped dns proxy server.", level="info")


def test_validation_no_transparent(monkeypatch):
    monkeypatch.setattr(mitmproxy.platform, "original_addr", None)
    ps = Proxyserver()
    with taddons.context(ps) as tctx:
        with pytest.raises(Exception, match="Transparent mode not supported"):
            tctx.configure(ps, mode=["transparent"])


def test_transparent_init(monkeypatch):
    init = Mock()
    monkeypatch.setattr(mitmproxy.platform, "original_addr", lambda: 1)
    monkeypatch.setattr(mitmproxy.platform, "init_transparent_mode", init)
    ps = Proxyserver()
    with taddons.context(ps) as tctx:
        tctx.configure(ps, mode=["transparent"], server=False)
        assert init.called
