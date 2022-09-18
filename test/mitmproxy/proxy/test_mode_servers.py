import asyncio
import platform
from typing import cast
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest

import mitmproxy.platform
from mitmproxy.addons.proxyserver import Proxyserver
from mitmproxy.net import udp
from mitmproxy.proxy.mode_servers import DnsInstance, ServerInstance
from mitmproxy.proxy.server import ConnectionHandler
from mitmproxy.test import taddons


def test_make():
    manager = Mock()
    context = MagicMock()
    assert ServerInstance.make("regular", manager)

    for mode in ["regular", "upstream:example.com", "transparent", "reverse:example.com", "socks5"]:
        inst = ServerInstance.make(mode, manager)
        assert inst
        assert inst.make_top_layer(context)
        assert inst.mode.description
        assert inst.to_json()


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


async def test_tcp_start_stop(caplog_async):
    caplog_async.set_level("INFO")
    manager = MagicMock()

    with taddons.context():
        inst = ServerInstance.make("regular@127.0.0.1:0", manager)
        await inst.start()
        assert inst.last_exception is None
        assert await caplog_async.await_log("proxy listening")

        host, port, *_ = inst.listen_addrs[0]
        reader, writer = await asyncio.open_connection(host, port)
        assert await caplog_async.await_log("client connect")

        writer.close()
        await writer.wait_closed()
        assert await caplog_async.await_log("client disconnect")

        await inst.stop()
        assert await caplog_async.await_log("Stopped HTTP(S) proxy")


@pytest.mark.parametrize("failure", [True, False])
async def test_transparent(failure, monkeypatch, caplog_async):
    caplog_async.set_level("INFO")
    manager = MagicMock()

    if failure:
        monkeypatch.setattr(mitmproxy.platform, "original_addr", None)
    else:
        monkeypatch.setattr(mitmproxy.platform, "original_addr", lambda s: ("address", 42))

    with taddons.context(Proxyserver()) as tctx:
        tctx.options.connection_strategy = "lazy"
        inst = ServerInstance.make("transparent@127.0.0.1:0", manager)
        await inst.start()
        await caplog_async.await_log("proxy listening")

        host, port, *_ = inst.listen_addrs[0]
        reader, writer = await asyncio.open_connection(host, port)

        if failure:
            assert await caplog_async.await_log("Transparent mode failure")
            writer.close()
            await writer.wait_closed()
        else:
            assert await caplog_async.await_log("client connect")
            writer.close()
            await writer.wait_closed()
            assert await caplog_async.await_log("client disconnect")

        await inst.stop()
        assert await caplog_async.await_log("Stopped transparent proxy")


async def test_wireguard(tdata, monkeypatch, caplog):
    caplog.set_level("DEBUG")

    async def handle_client(self: ConnectionHandler):
        t = self.transports[self.client]
        data = await t.reader.read(65535)
        t.writer.write(data.upper())
        await t.writer.drain()
        t.writer.close()

    monkeypatch.setattr(ConnectionHandler, "handle_client", handle_client)

    system = platform.system()
    if system == "Linux":
        test_client_name = "linux-x86_64"
    elif system == "Darwin":
        test_client_name = "macos-x86_64"
    elif system == "Windows":
        test_client_name = "windows-x86_64.exe"
    else:
        return pytest.skip("Unsupported platform for wg-test-client.")

    test_client_path = tdata.path(f"wg-test-client/{test_client_name}")
    test_conf = tdata.path(f"wg-test-client/test.conf")

    with taddons.context(Proxyserver()):
        inst = ServerInstance.make(f"wireguard:{test_conf}", MagicMock())

        await inst.start()
        assert "WireGuard server listening" in caplog.text

        _, port = inst.listen_addrs[0]

        proc = await asyncio.create_subprocess_exec(
            test_client_path,
            str(port),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()

        try:
            assert proc.returncode == 0
        except AssertionError:
            print(stdout)
            print(stderr)
            raise

        await inst.stop()
        assert "Stopped WireGuard server" in caplog.text


async def test_tcp_start_error():
    manager = MagicMock()

    server = await asyncio.start_server(MagicMock(), host="127.0.0.1", port=0, reuse_address=False)
    port = server.sockets[0].getsockname()[1]

    with taddons.context() as tctx:
        inst = ServerInstance.make(f"regular@127.0.0.1:{port}", manager)
        with pytest.raises(OSError, match=f"proxy failed to listen on 127\\.0\\.0\\.1:{port}"):
            await inst.start()
        tctx.options.listen_host = "127.0.0.1"
        tctx.options.listen_port = port
        inst3 = ServerInstance.make(f"regular", manager)
        with pytest.raises(OSError):
            await inst3.start()


async def test_invalid_protocol(monkeypatch):
    manager = MagicMock()

    with taddons.context():
        inst = ServerInstance.make(f"regular@127.0.0.1:0", manager)
        monkeypatch.setattr(inst.mode, "transport_protocol", "invalid_proto")
        with pytest.raises(AssertionError, match=f"invalid_proto"):
            await inst.start()


async def test_udp_start_stop(caplog_async):
    caplog_async.set_level("INFO")
    manager = MagicMock()
    manager.connections = {}

    with taddons.context():
        inst = ServerInstance.make("dns@127.0.0.1:0", manager)
        await inst.start()
        assert await caplog_async.await_log("server listening")

        host, port, *_ = inst.listen_addrs[0]
        reader, writer = await udp.open_connection(host, port)

        writer.write(b"\x00\x00\x01")
        assert await caplog_async.await_log("sent an invalid message")

        writer.close()

        await inst.stop()
        assert await caplog_async.await_log("Stopped")


async def test_udp_start_error():
    manager = MagicMock()

    with taddons.context():
        inst = ServerInstance.make("dns@127.0.0.1:0", manager)
        await inst.start()
        port = inst.listen_addrs[0][1]
        inst2 = ServerInstance.make(f"dns@127.0.0.1:{port}", manager)
        with pytest.raises(OSError, match=f"server failed to listen on 127\\.0\\.0\\.1:{port}"):
            await inst2.start()
        await inst.stop()


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
