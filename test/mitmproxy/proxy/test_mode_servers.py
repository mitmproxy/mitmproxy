import asyncio
from typing import cast
from unittest.mock import AsyncMock, MagicMock, Mock

from mitmproxy.net import udp
from mitmproxy.proxy.mode_servers import DnsInstance, ServerInstance
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


async def test_tcp_start_stop():
    manager = MagicMock()

    with taddons.context() as tctx:
        inst = ServerInstance.make("regular@127.0.0.1:0", manager)
        await inst.start()
        assert await tctx.master.await_log("proxy listening")

        host, port, *_ = inst.listen_addrs[0]
        reader, writer = await asyncio.open_connection(host, port)
        assert await tctx.master.await_log("client connect")

        writer.close()
        await writer.wait_closed()
        assert await tctx.master.await_log("client disconnect")

        await inst.stop()
        assert await tctx.master.await_log("Stopped regular proxy server.")


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


async def test_udp_connection_reuse(monkeypatch):
    manager = MagicMock()
    manager.connections = {}

    monkeypatch.setattr(udp, "DatagramWriter", MagicMock())
    monkeypatch.setattr(DnsInstance, "handle_dns_connection", AsyncMock())

    with taddons.context():
        inst = cast(DnsInstance, ServerInstance.make("dns", manager))
        inst.handle_dns_datagram(MagicMock(), b"\x00\x00\x01", ("remoteaddr", 0), ("localaddr", 0))
        inst.handle_dns_datagram(MagicMock(), b"\x00\x00\x02", ("remoteaddr", 0), ("localaddr", 0))
        await asyncio.sleep(0)

        assert len(inst.manager.connections) == 1
