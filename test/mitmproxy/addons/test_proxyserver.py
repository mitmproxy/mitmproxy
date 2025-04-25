from __future__ import annotations

import asyncio
import ssl
from collections.abc import AsyncGenerator
from collections.abc import Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any
from typing import ClassVar
from typing import TypeVar
from unittest.mock import Mock

import pytest
from aioquic.asyncio.protocol import QuicConnectionProtocol
from aioquic.asyncio.server import QuicServer
from aioquic.h3 import events as h3_events
from aioquic.h3.connection import FrameUnexpected
from aioquic.h3.connection import H3Connection
from aioquic.quic import events as quic_events
from aioquic.quic.configuration import QuicConfiguration
from aioquic.quic.connection import QuicConnection
from aioquic.quic.connection import QuicConnectionError

from .test_clientplayback import tcp_server
import mitmproxy.platform
import mitmproxy_rs
from mitmproxy import dns
from mitmproxy import exceptions
from mitmproxy.addons import dns_resolver
from mitmproxy.addons.next_layer import NextLayer
from mitmproxy.addons.proxyserver import Proxyserver
from mitmproxy.addons.tlsconfig import TlsConfig
from mitmproxy.connection import Address
from mitmproxy.proxy import layers
from mitmproxy.proxy import server_hooks
from mitmproxy.test import taddons
from mitmproxy.test import tflow
from mitmproxy.test.tflow import tclient_conn
from mitmproxy.test.tflow import tserver_conn
from mitmproxy.test.tutils import tdnsreq
from mitmproxy.utils import data

tlsdata = data.Data(__name__)


class HelperAddon:
    def __init__(self):
        self.flows = []

    def request(self, f):
        self.flows.append(f)

    def tcp_start(self, f):
        self.flows.append(f)


async def test_start_stop(caplog_async):
    caplog_async.set_level("INFO")

    async def server_handler(
        reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ):
        assert await reader.readuntil(b"\r\n\r\n") == b"GET /hello HTTP/1.1\r\n\r\n"
        writer.write(b"HTTP/1.1 204 No Content\r\n\r\n")
        await writer.drain()

    ps = Proxyserver()
    nl = NextLayer()
    state = HelperAddon()

    with taddons.context(ps, nl, state) as tctx:
        async with tcp_server(server_handler) as addr:
            tctx.configure(ps, listen_host="127.0.0.1", listen_port=0)
            assert not ps.servers
            assert await ps.setup_servers()
            ps.running()
            await caplog_async.await_log("HTTP(S) proxy listening at")
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
            assert ps.active_connections() == 1

            await (
                ps.setup_servers()
            )  # assert this can always be called without side effects
            tctx.configure(ps, server=False)
            await caplog_async.await_log("stopped")
            if ps.servers.is_updating:
                async with ps.servers._lock:
                    pass  # wait until start/stop is finished.
            assert not ps.servers
            assert state.flows
            assert state.flows[0].request.path == "/hello"
            assert state.flows[0].response.status_code == 204

            writer.close()
            await writer.wait_closed()
            await _wait_for_connection_closes(ps)


async def _wait_for_connection_closes(ps: Proxyserver):
    # Waiting here until everything is really torn down... takes some effort.
    client_handlers = [
        conn_handler.transports[conn_handler.client].handler
        for conn_handler in ps.connections.values()
        if conn_handler.client in conn_handler.transports
    ]
    for client_handler in client_handlers:
        try:
            await asyncio.wait_for(client_handler, 5)
        except asyncio.CancelledError:
            pass
    for _ in range(5):
        # Get all other scheduled coroutines to run.
        await asyncio.sleep(0)
    assert not ps.connections


async def test_inject() -> None:
    async def server_handler(
        reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ):
        while s := await reader.read(1):
            writer.write(s.upper())

    ps = Proxyserver()
    nl = NextLayer()
    state = HelperAddon()

    with taddons.context(ps, nl, state) as tctx:
        async with tcp_server(server_handler) as addr:
            tctx.configure(ps, listen_host="127.0.0.1", listen_port=0)
            assert await ps.setup_servers()
            ps.running()
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

            writer.close()
            await writer.wait_closed()
            await _wait_for_connection_closes(ps)


async def test_inject_fail(caplog) -> None:
    ps = Proxyserver()
    ps.inject_websocket(tflow.tflow(), True, b"test")
    assert "Cannot inject WebSocket messages into non-WebSocket flows." in caplog.text
    ps.inject_tcp(tflow.tflow(), True, b"test")
    assert "Cannot inject TCP messages into non-TCP flows." in caplog.text

    ps.inject_udp(tflow.tflow(), True, b"test")
    assert "Cannot inject UDP messages into non-UDP flows." in caplog.text
    ps.inject_udp(tflow.tudpflow(), True, b"test")
    assert "Flow is not from a live connection." in caplog.text

    ps.inject_websocket(tflow.twebsocketflow(), True, b"test")
    assert "Flow is not from a live connection." in caplog.text
    ps.inject_websocket(tflow.ttcpflow(), True, b"test")
    assert "Cannot inject WebSocket messages into non-WebSocket flows" in caplog.text


async def test_warn_no_nextlayer(caplog):
    """
    Test that we log an error if the proxy server is started without NextLayer addon.
    That is a mean trap to fall into when writing end-to-end tests.
    """
    ps = Proxyserver()
    with taddons.context(ps) as tctx:
        tctx.configure(ps, listen_host="127.0.0.1", listen_port=0, server=False)
        assert await ps.setup_servers()
        ps.running()
        assert "Warning: Running proxyserver without nextlayer addon!" in caplog.text


async def test_self_connect():
    server = tserver_conn()
    client = tclient_conn()
    server.address = ("localhost", 8080)
    ps = Proxyserver()
    with taddons.context(ps) as tctx:
        tctx.configure(ps, listen_host="127.0.0.1", listen_port=0)
        assert await ps.setup_servers()
        ps.running()
        assert ps.servers
        server.address = ("localhost", ps.servers["regular"].listen_addrs[0][1])
        ps.server_connect(server_hooks.ServerConnectionHookData(server, client))
        assert "Request destination unknown" in server.error
        tctx.configure(ps, server=False)
        assert await ps.setup_servers()
        await _wait_for_connection_closes(ps)


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
        tctx.configure(ps, mode=["regular", "local"], server=False)


async def test_startup_err(monkeypatch, caplog) -> None:
    async def _raise(*_):
        raise OSError("cannot bind")

    monkeypatch.setattr(asyncio, "start_server", _raise)

    ps = Proxyserver()
    with taddons.context(ps):
        assert not await ps.setup_servers()
        assert "cannot bind" in caplog.text


async def test_shutdown_err(caplog_async) -> None:
    caplog_async.set_level("INFO")

    async def _raise(*_):
        raise OSError("cannot close")

    ps = Proxyserver()
    with taddons.context(ps) as tctx:
        tctx.configure(ps, listen_host="127.0.0.1", listen_port=0)
        assert await ps.setup_servers()
        ps.running()
        assert ps.servers
        for server in ps.servers:
            setattr(server, "stop", _raise)
        tctx.configure(ps, server=False)
        await caplog_async.await_log("cannot close")
        await _wait_for_connection_closes(ps)


async def lookup_ipv4():
    return await asyncio.sleep(0, ["8.8.8.8"])


async def test_dns(caplog_async, monkeypatch) -> None:
    monkeypatch.setattr(
        mitmproxy_rs.dns.DnsResolver, "lookup_ipv4", lambda _, __: lookup_ipv4()
    )

    caplog_async.set_level("INFO")
    ps = Proxyserver()
    with taddons.context(ps, dns_resolver.DnsResolver()) as tctx:
        tctx.configure(
            ps,
            mode=["dns@127.0.0.1:0"],
        )
        assert await ps.setup_servers()
        ps.running()
        await caplog_async.await_log("DNS server listening at")
        assert ps.servers
        dns_addr = ps.servers["dns@127.0.0.1:0"].listen_addrs[0]
        s = await mitmproxy_rs.udp.open_udp_connection(*dns_addr)
        req = tdnsreq()
        s.write(req.packed)
        resp = dns.DNSMessage.unpack(await s.read(65535))
        assert req.id == resp.id and "8.8.8.8" in str(resp)
        assert len(ps.connections) == 1
        s.write(req.packed)
        resp = dns.DNSMessage.unpack(await s.read(65535))
        assert req.id == resp.id and "8.8.8.8" in str(resp)
        assert len(ps.connections) == 1
        req.id = req.id + 1
        s.write(req.packed)
        resp = dns.DNSMessage.unpack(await s.read(65535))
        assert req.id == resp.id and "8.8.8.8" in str(resp)
        assert len(ps.connections) == 1
        (dns_conn,) = ps.connections.values()
        assert isinstance(dns_conn.layer, layers.DNSLayer)
        assert len(dns_conn.layer.flows) == 2

        s.write(b"\x00")
        await caplog_async.await_log("sent an invalid message")
        tctx.configure(ps, server=False)
        await caplog_async.await_log("stopped")

        s.close()
        await s.wait_closed()
        await _wait_for_connection_closes(ps)


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


@asynccontextmanager
async def udp_server(
    handle_datagram: Callable[
        [asyncio.DatagramTransport, bytes, tuple[str, int]], None
    ],
) -> Address:
    class ServerProtocol(asyncio.DatagramProtocol):
        def connection_made(self, transport):
            self.transport = transport

        def datagram_received(self, data, addr):
            handle_datagram(self.transport, data, addr)

    loop = asyncio.get_running_loop()
    transport, _ = await loop.create_datagram_endpoint(
        lambda: ServerProtocol(),
        local_addr=("127.0.0.1", 0),
    )
    socket = transport.get_extra_info("socket")

    try:
        yield socket.getsockname()
    finally:
        transport.close()


async def test_udp(caplog_async) -> None:
    caplog_async.set_level("INFO")

    def handle_datagram(
        transport: asyncio.DatagramTransport,
        data: bytes,
        remote_addr: Address,
    ):
        assert data == b"\x16"
        transport.sendto(b"\x01", remote_addr)

    ps = Proxyserver()
    nl = NextLayer()

    with taddons.context(ps, nl) as tctx:
        async with udp_server(handle_datagram) as server_addr:
            mode = f"reverse:udp://{server_addr[0]}:{server_addr[1]}@127.0.0.1:0"
            tctx.configure(ps, mode=[mode])
            assert await ps.setup_servers()
            ps.running()
            await caplog_async.await_log(
                f"reverse proxy to udp://{server_addr[0]}:{server_addr[1]} listening"
            )
            assert ps.servers
            addr = ps.servers[mode].listen_addrs[0]
            stream = await mitmproxy_rs.udp.open_udp_connection(*addr)
            stream.write(b"\x16")
            assert b"\x01" == await stream.read(65535)
            assert repr(ps) == "Proxyserver(1 active conns)"
            assert len(ps.connections) == 1
            tctx.configure(ps, server=False)
            await caplog_async.await_log("stopped")

        stream.close()
        await stream.wait_closed()
        await _wait_for_connection_closes(ps)


class H3EchoServer(QuicConnectionProtocol):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._seen_headers: set[int] = set()
        self.http: H3Connection | None = None

    def http_headers_received(self, event: h3_events.HeadersReceived) -> None:
        assert event.push_id is None
        headers: dict[bytes, bytes] = {}
        for name, value in event.headers:
            headers[name] = value
        response = []
        if event.stream_id not in self._seen_headers:
            self._seen_headers.add(event.stream_id)
            assert headers[b":authority"] == b"example.mitmproxy.org"
            assert headers[b":method"] == b"GET"
            assert headers[b":path"] == b"/test"
            response.append((b":status", b"200"))
        response.append((b"x-response", headers[b"x-request"]))
        self.http.send_headers(
            stream_id=event.stream_id, headers=response, end_stream=event.stream_ended
        )
        self.transmit()

    def http_data_received(self, event: h3_events.DataReceived) -> None:
        assert event.push_id is None
        assert event.stream_id in self._seen_headers
        try:
            self.http.send_data(
                stream_id=event.stream_id,
                data=event.data,
                end_stream=event.stream_ended,
            )
        except FrameUnexpected:
            if event.data or not event.stream_ended:
                raise
            self._quic.send_stream_data(
                stream_id=event.stream_id,
                data=b"",
                end_stream=True,
            )
        self.transmit()

    def http_event_received(self, event: h3_events.H3Event) -> None:
        if isinstance(event, h3_events.HeadersReceived):
            self.http_headers_received(event)
        elif isinstance(event, h3_events.DataReceived):
            self.http_data_received(event)
        else:
            raise AssertionError(event)

    def quic_event_received(self, event: quic_events.QuicEvent) -> None:
        if isinstance(event, quic_events.ProtocolNegotiated):
            self.http = H3Connection(self._quic)
        if self.http is not None:
            for http_event in self.http.handle_event(event):
                self.http_event_received(http_event)


class QuicDatagramEchoServer(QuicConnectionProtocol):
    def quic_event_received(self, event: quic_events.QuicEvent) -> None:
        if isinstance(event, quic_events.DatagramFrameReceived):
            self._quic.send_datagram_frame(event.data)
            self.transmit()


@asynccontextmanager
async def quic_server(
    create_protocol, alpn: list[str]
) -> AsyncGenerator[Address, None]:
    configuration = QuicConfiguration(
        is_client=False,
        alpn_protocols=alpn,
        max_datagram_frame_size=65536,
    )
    configuration.load_cert_chain(
        certfile=tlsdata.path("../net/data/verificationcerts/trusted-leaf.crt"),
        keyfile=tlsdata.path("../net/data/verificationcerts/trusted-leaf.key"),
    )
    loop = asyncio.get_running_loop()
    transport, server = await loop.create_datagram_endpoint(
        lambda: QuicServer(
            configuration=configuration,
            create_protocol=create_protocol,
        ),
        local_addr=("127.0.0.1", 0),
    )
    try:
        yield transport.get_extra_info("sockname")
    finally:
        server.close()


class QuicClient(QuicConnectionProtocol):
    TIMEOUT: ClassVar[int] = 10

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._waiter = self._loop.create_future()

    def quic_event_received(self, event: quic_events.QuicEvent) -> None:
        if not self._waiter.done():
            if isinstance(event, quic_events.ConnectionTerminated):
                self._waiter.set_exception(
                    QuicConnectionError(
                        event.error_code, event.frame_type, event.reason_phrase
                    )
                )
            elif isinstance(event, quic_events.HandshakeCompleted):
                self._waiter.set_result(None)

    def connection_lost(self, exc: Exception | None) -> None:
        if not self._waiter.done():
            self._waiter.set_exception(exc)
        return super().connection_lost(exc)

    async def wait_handshake(self) -> None:
        return await asyncio.wait_for(self._waiter, timeout=QuicClient.TIMEOUT)


class QuicDatagramClient(QuicClient):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._datagram: asyncio.Future[bytes] = self._loop.create_future()

    def quic_event_received(self, event: quic_events.QuicEvent) -> None:
        super().quic_event_received(event)
        if not self._datagram.done():
            if isinstance(event, quic_events.DatagramFrameReceived):
                self._datagram.set_result(event.data)
            elif isinstance(event, quic_events.ConnectionTerminated):
                self._datagram.set_exception(
                    QuicConnectionError(
                        event.error_code, event.frame_type, event.reason_phrase
                    )
                )

    def send_datagram(self, data: bytes) -> None:
        self._quic.send_datagram_frame(data)
        self.transmit()

    async def recv_datagram(self) -> bytes:
        return await asyncio.wait_for(self._datagram, timeout=QuicClient.TIMEOUT)


@dataclass
class H3Response:
    waiter: asyncio.Future[H3Response]
    stream_id: int
    headers: h3_events.H3Event | None = None
    data: bytes | None = None
    trailers: h3_events.H3Event | None = None
    callback: Callable[[str], None] | None = None

    async def wait_result(self) -> H3Response:
        return await asyncio.wait_for(self.waiter, timeout=QuicClient.TIMEOUT)

    def __setattr__(self, name: str, value: Any) -> None:
        super().__setattr__(name, value)
        if self.callback:
            self.callback(name)


class H3Client(QuicClient):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._responses: dict[int, H3Response] = dict()
        self.http = H3Connection(self._quic)

    def http_headers_received(self, event: h3_events.HeadersReceived) -> None:
        assert event.push_id is None
        response = self._responses[event.stream_id]
        if response.waiter.done():
            return
        if response.headers is None:
            response.headers = event.headers
            if event.stream_ended:
                response.waiter.set_result(response)
        elif response.trailers is None:
            response.trailers = event.headers
            if event.stream_ended:
                response.waiter.set_result(response)
        else:
            response.waiter.set_exception(Exception("Headers after trailers received."))

    def http_data_received(self, event: h3_events.DataReceived) -> None:
        assert event.push_id is None
        response = self._responses[event.stream_id]
        if response.waiter.done():
            return
        if response.headers is None:
            response.waiter.set_exception(Exception("Data without headers received."))
        elif response.trailers is None:
            if response.data is None:
                response.data = event.data
            else:
                response.data = response.data + event.data
            if event.stream_ended:
                response.waiter.set_result(response)
        elif event.data or not event.stream_ended:
            response.waiter.set_exception(Exception("Data after trailers received."))
        else:
            response.waiter.set_result(response)

    def http_event_received(self, event: h3_events.H3Event) -> None:
        if isinstance(event, h3_events.HeadersReceived):
            self.http_headers_received(event)
        elif isinstance(event, h3_events.DataReceived):
            self.http_data_received(event)
        else:
            raise AssertionError(event)

    def quic_event_received(self, event: quic_events.QuicEvent) -> None:
        super().quic_event_received(event)
        for http_event in self.http.handle_event(event):
            self.http_event_received(http_event)

    def request(
        self,
        headers: h3_events.Headers,
        data: bytes | None = None,
        trailers: h3_events.Headers | None = None,
        end_stream: bool = True,
    ) -> H3Response:
        stream_id = self._quic.get_next_available_stream_id()
        self.http.send_headers(
            stream_id=stream_id,
            headers=headers,
            end_stream=data is None and trailers is None and end_stream,
        )
        if data is not None:
            self.http.send_data(
                stream_id=stream_id,
                data=data,
                end_stream=trailers is None and end_stream,
            )
        if trailers is not None:
            self.http.send_headers(
                stream_id=stream_id,
                headers=trailers,
                end_stream=end_stream,
            )
        waiter = self._loop.create_future()
        response = H3Response(waiter=waiter, stream_id=stream_id)
        self._responses[stream_id] = response
        self.transmit()
        return response


T = TypeVar("T", bound=QuicClient)


@asynccontextmanager
async def quic_connect(
    cls: type[T],
    alpn: list[str],
    address: Address,
) -> AsyncGenerator[T, None]:
    configuration = QuicConfiguration(
        is_client=True,
        alpn_protocols=alpn,
        server_name="example.mitmproxy.org",
        verify_mode=ssl.CERT_NONE,
        max_datagram_frame_size=65536,
    )
    loop = asyncio.get_running_loop()
    transport, protocol = await loop.create_datagram_endpoint(
        lambda: cls(QuicConnection(configuration=configuration)),
        local_addr=("127.0.0.1", 0),
    )
    assert isinstance(protocol, cls)
    try:
        protocol.connect(address)
        await protocol.wait_handshake()
        yield protocol
    finally:
        protocol.close()
        await protocol.wait_closed()
        transport.close()


async def _test_echo(client: H3Client, strict: bool) -> None:
    def assert_no_data(response: H3Response):
        if strict:
            assert response.data is None
        else:
            assert not response.data

    headers = [
        (b":scheme", b"https"),
        (b":authority", b"example.mitmproxy.org"),
        (b":method", b"GET"),
        (b":path", b"/test"),
    ]
    r1 = await client.request(
        headers=headers + [(b"x-request", b"justheaders")],
        data=None,
        trailers=None,
    ).wait_result()
    assert r1.headers == [
        (b":status", b"200"),
        (b"x-response", b"justheaders"),
    ]
    assert_no_data(r1)
    assert r1.trailers is None

    r2 = await client.request(
        headers=headers + [(b"x-request", b"hasdata")],
        data=b"echo",
        trailers=None,
    ).wait_result()
    assert r2.headers == [
        (b":status", b"200"),
        (b"x-response", b"hasdata"),
    ]
    assert r2.data == b"echo"
    assert r2.trailers is None

    r3 = await client.request(
        headers=headers + [(b"x-request", b"nodata")],
        data=None,
        trailers=[(b"x-request", b"buttrailers")],
    ).wait_result()
    assert r3.headers == [
        (b":status", b"200"),
        (b"x-response", b"nodata"),
    ]
    assert_no_data(r3)
    assert r3.trailers == [(b"x-response", b"buttrailers")]

    r4 = await client.request(
        headers=headers + [(b"x-request", b"this")],
        data=b"has",
        trailers=[(b"x-request", b"everything")],
    ).wait_result()
    assert r4.headers == [
        (b":status", b"200"),
        (b"x-response", b"this"),
    ]
    assert r4.data == b"has"
    assert r4.trailers == [(b"x-response", b"everything")]

    # the following test makes sure that we behave properly if end_stream is sent separately
    r5 = client.request(
        headers=headers + [(b"x-request", b"this")],
        data=b"has",
        trailers=[(b"x-request", b"everything but end_stream")],
        end_stream=False,
    )
    if not strict:
        trailer_waiter = asyncio.get_running_loop().create_future()
        r5.callback = lambda name: name != "trailers" or trailer_waiter.set_result(None)
        await asyncio.wait_for(trailer_waiter, timeout=QuicClient.TIMEOUT)
        assert r5.trailers is not None
        assert not r5.waiter.done()
    else:
        await asyncio.sleep(0)
    client._quic.send_stream_data(
        stream_id=r5.stream_id,
        data=b"",
        end_stream=True,
    )
    client.transmit()
    await r5.wait_result()
    assert r5.headers == [
        (b":status", b"200"),
        (b"x-response", b"this"),
    ]
    assert r5.data == b"has"
    assert r5.trailers == [(b"x-response", b"everything but end_stream")]


@pytest.mark.parametrize("scheme", ["http3", "quic"])
async def test_reverse_http3_and_quic_stream(caplog_async, scheme: str) -> None:
    caplog_async.set_level("INFO")
    ps = Proxyserver()
    nl = NextLayer()
    ta = TlsConfig()
    with taddons.context(ps, nl, ta) as tctx:
        tctx.options.keep_host_header = True
        ta.configure(["confdir"])
        async with quic_server(H3EchoServer, alpn=["h3"]) as server_addr:
            mode = f"reverse:{scheme}://{server_addr[0]}:{server_addr[1]}@127.0.0.1:0"
            tctx.configure(
                ta,
                ssl_verify_upstream_trusted_ca=tlsdata.path(
                    "../net/data/verificationcerts/trusted-root.crt"
                ),
            )
            tctx.configure(ps, mode=[mode])
            assert await ps.setup_servers()
            ps.running()
            await caplog_async.await_log(
                f"reverse proxy to {scheme}://{server_addr[0]}:{server_addr[1]} listening"
            )
            assert ps.servers
            addr = ps.servers[mode].listen_addrs[0]
            async with quic_connect(H3Client, alpn=["h3"], address=addr) as client:
                await _test_echo(client, strict=scheme == "http3")
                assert len(ps.connections) == 1

            tctx.configure(ps, server=False)
            await caplog_async.await_log(f"stopped")
            await _wait_for_connection_closes(ps)


async def test_reverse_quic_datagram(caplog_async) -> None:
    caplog_async.set_level("INFO")
    ps = Proxyserver()
    nl = NextLayer()
    ta = TlsConfig()
    with taddons.context(ps, nl, ta) as tctx:
        tctx.options.keep_host_header = True
        ta.configure(["confdir"])
        async with quic_server(QuicDatagramEchoServer, alpn=["dgram"]) as server_addr:
            mode = f"reverse:quic://{server_addr[0]}:{server_addr[1]}@127.0.0.1:0"
            tctx.configure(
                ta,
                ssl_verify_upstream_trusted_ca=tlsdata.path(
                    "../net/data/verificationcerts/trusted-root.crt"
                ),
            )
            tctx.configure(ps, mode=[mode])
            assert await ps.setup_servers()
            ps.running()
            await caplog_async.await_log(
                f"reverse proxy to quic://{server_addr[0]}:{server_addr[1]} listening"
            )
            assert ps.servers
            addr = ps.servers[mode].listen_addrs[0]
            async with quic_connect(
                QuicDatagramClient, alpn=["dgram"], address=addr
            ) as client:
                client.send_datagram(b"echo")
                assert await client.recv_datagram() == b"echo"

            tctx.configure(ps, server=False)
            await caplog_async.await_log("stopped")
            await _wait_for_connection_closes(ps)


@pytest.mark.skip("HTTP/3 for regular mode is not fully supported yet")
async def test_regular_http3(caplog_async, monkeypatch) -> None:
    caplog_async.set_level("INFO")
    ps = Proxyserver()
    nl = NextLayer()
    ta = TlsConfig()
    with taddons.context(ps, nl, ta) as tctx:
        ta.configure(["confdir"])
        async with quic_server(H3EchoServer, alpn=["h3"]) as server_addr:
            orig_open_connection = mitmproxy_rs.udp.open_udp_connection

            async def open_connection_path(
                host: str, port: int, *args, **kwargs
            ) -> mitmproxy_rs.Stream:
                if host == "example.mitmproxy.org" and port == 443:
                    host = server_addr[0]
                    port = server_addr[1]
                return orig_open_connection(host, port, *args, **kwargs)

            monkeypatch.setattr(
                mitmproxy_rs.udp, "open_udp_connection", open_connection_path
            )
            mode = f"http3@127.0.0.1:0"
            tctx.configure(
                ta,
                ssl_verify_upstream_trusted_ca=tlsdata.path(
                    "../net/data/verificationcerts/trusted-root.crt"
                ),
            )
            tctx.configure(ps, mode=[mode])
            assert await ps.setup_servers()
            ps.running()
            await caplog_async.await_log(f"HTTP3 proxy listening")
            assert ps.servers
            addr = ps.servers[mode].listen_addrs[0]
            async with quic_connect(H3Client, alpn=["h3"], address=addr) as client:
                await _test_echo(client=client, strict=True)
                assert len(ps.connections) == 1

            tctx.configure(ps, server=False)
            await caplog_async.await_log("stopped")
            await _wait_for_connection_closes(ps)
