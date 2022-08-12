import asyncio
from typing import cast
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest

from mitmproxy.net import udp
from mitmproxy.proxy.mode_servers import DnsInstance, ServerInstance, DtlsInstance
from mitmproxy.test import taddons


def test_make():
    manager = Mock()
    context = MagicMock()
    assert ServerInstance.make("regular", manager)

    for mode in ["regular", "upstream:example.com", "transparent", "reverse:example.com", "socks5"]:
        inst = ServerInstance.make(mode, manager)
        assert inst
        assert inst.make_top_layer(context)
        assert inst.log_desc


async def test_last_exception_and_running(monkeypatch):
    manager = MagicMock()
    err = ValueError("something else")

    async def _raise(*_):
        nonlocal err
        raise err

    with taddons.context():

        inst1 = ServerInstance.make("regular@127.0.0.1:0", manager)
        await inst1.start()
        assert inst1.last_exception is None
        assert inst1.is_running
        monkeypatch.setattr(inst1._server, "wait_closed", _raise)
        with pytest.raises(type(err), match=str(err)):
            await inst1.stop()
        assert inst1.last_exception is err

        monkeypatch.setattr(asyncio, "start_server", _raise)
        inst2 = ServerInstance.make("regular@127.0.0.1:0", manager)
        assert inst2.last_exception is None
        with pytest.raises(type(err), match=str(err)):
            await inst2.start()
        assert inst2.last_exception is err
        assert not inst1.is_running


async def test_tcp_start_stop():
    manager = MagicMock()

    with taddons.context() as tctx:
        inst = ServerInstance.make("regular@127.0.0.1:0", manager)
        await inst.start()
        assert inst.last_exception is None
        assert await tctx.master.await_log("proxy listening")

        host, port, *_ = inst.listen_addrs[0]
        reader, writer = await asyncio.open_connection(host, port)
        assert await tctx.master.await_log("client connect")

        writer.close()
        await writer.wait_closed()
        assert await tctx.master.await_log("client disconnect")

        await inst.stop()
        assert await tctx.master.await_log("stopped HTTP(S) proxy")


async def test_tcp_start_error():
    manager = MagicMock()

    with taddons.context() as tctx:
        inst = ServerInstance.make("regular@127.0.0.1:0", manager)
        await inst.start()
        assert inst.last_exception is None
        assert await tctx.master.await_log("proxy listening")
        port = inst.listen_addrs[0][1]
        inst2 = ServerInstance.make(f"regular@127.0.0.1:{port}", manager)
        with pytest.raises(OSError, match=f"proxy failed to listen on 127\\.0\\.0\\.1:{port}"):
            await inst2.start()
        tctx.options.listen_host = "127.0.0.1"
        tctx.options.listen_port = port
        inst3 = ServerInstance.make(f"regular", manager)
        with pytest.raises(OSError):
            await inst3.start()


async def test_udp_start_stop():
    manager = MagicMock()

    with taddons.context() as tctx:
        inst = ServerInstance.make("dns@127.0.0.1:0", manager)
        await inst.start()
        assert await tctx.master.await_log("server listening")

        host, port, *_ = inst.listen_addrs[0]
        reader, writer = await udp.open_connection(host, port)
        writer.write(b"\x00")
        assert await tctx.master.await_log("Invalid DNS datagram received")

        writer.write(b"\x00\x00\x01")
        assert await tctx.master.await_log("sent an invalid message")

        writer.close()

        await inst.stop()
        assert await tctx.master.await_log("Stopped")


async def test_udp_start_error():
    manager = MagicMock()

    with taddons.context() as tctx:
        inst = ServerInstance.make("dns@127.0.0.1:0", manager)
        await inst.start()
        assert await tctx.master.await_log("server listening")
        port = inst.listen_addrs[0][1]
        inst2 = ServerInstance.make(f"dns@127.0.0.1:{port}", manager)
        with pytest.raises(OSError, match=f"server failed to listen on 127\\.0\\.0\\.1:{port}"):
            await inst2.start()


async def test_dtls_start_stop(monkeypatch):
    manager = MagicMock()

    with taddons.context() as tctx:
        inst = ServerInstance.make("dtls:reverse:127.0.0.1:0@127.0.0.1:0", manager)
        await inst.start()
        assert await tctx.master.await_log("server listening")

        host, port, *_ = inst.listen_addrs[0]
        reader, writer = await udp.open_connection(host, port)

        writer.close()
        await inst.stop()
        assert await tctx.master.await_log("Stopped")


async def test_udp_connection_reuse(monkeypatch):
    manager = MagicMock()
    manager.connections = {}

    monkeypatch.setattr(udp, "DatagramWriter", MagicMock())
    monkeypatch.setattr(DnsInstance, "handle_udp_connection", AsyncMock())

    with taddons.context():
        inst = cast(DnsInstance, ServerInstance.make("dns", manager))
        inst.handle_udp_datagram(MagicMock(), b"\x00\x00\x01", ("remoteaddr", 0), ("localaddr", 0))
        inst.handle_udp_datagram(MagicMock(), b"\x00\x00\x02", ("remoteaddr", 0), ("localaddr", 0))
        await asyncio.sleep(0)

        assert len(inst.manager.connections) == 1


async def test_dtls_connection_reuse(monkeypatch):
    manager = MagicMock()
    manager.connections = {}

    monkeypatch.setattr(udp, "DatagramWriter", MagicMock())
    monkeypatch.setattr(DtlsInstance, "handle_udp_connection", AsyncMock())

    with taddons.context():
        inst = cast(DtlsInstance, ServerInstance.make("dtls:reverse:127.0.0.1:0", manager))
        inst.handle_udp_datagram(MagicMock(), b"\x00\x00\x01", ("remoteaddr", 0), ("localaddr", 0))
        inst.handle_udp_datagram(MagicMock(), b"\x00\x00\x02", ("remoteaddr", 0), ("localaddr", 0))
        await asyncio.sleep(0)

        assert len(inst.manager.connections) == 1
