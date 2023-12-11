import asyncio
import platform
from typing import cast
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import Mock

import mitmproxy_rs
import pytest

import mitmproxy.platform
from mitmproxy.addons.proxyserver import Proxyserver
from mitmproxy.net import udp
from mitmproxy.proxy.mode_servers import DnsInstance
from mitmproxy.proxy.mode_servers import LocalRedirectorInstance
from mitmproxy.proxy.mode_servers import ServerInstance
from mitmproxy.proxy.mode_servers import WireGuardServerInstance
from mitmproxy.proxy.server import ConnectionHandler
from mitmproxy.test import taddons


def test_make():
    manager = Mock()
    context = MagicMock()
    assert ServerInstance.make("regular", manager)

    for mode in [
        "regular",
        # "http3",
        "upstream:example.com",
        "transparent",
        "reverse:example.com",
        "socks5",
    ]:
        inst = ServerInstance.make(mode, manager)
        assert inst
        assert inst.make_top_layer(context)
        assert inst.mode.description
        assert inst.to_json()

    with pytest.raises(
        ValueError, match="is not a spec for a WireGuardServerInstance server."
    ):
        WireGuardServerInstance.make("regular", manager)


async def test_last_exception_and_running(monkeypatch):
    manager = MagicMock()
    err = ValueError("something else")

    def _raise(*_):
        nonlocal err
        raise err

    async def _raise_async(*_):
        nonlocal err
        raise err

    with taddons.context():
        inst1 = ServerInstance.make("regular@127.0.0.1:0", manager)
        await inst1.start()
        assert inst1.last_exception is None
        assert inst1.is_running
        monkeypatch.setattr(inst1._servers[0], "close", _raise)
        with pytest.raises(type(err), match=str(err)):
            await inst1.stop()
        assert inst1.last_exception is err

        monkeypatch.setattr(asyncio, "start_server", _raise_async)
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
        assert await caplog_async.await_log("stopped")


@pytest.mark.parametrize("failure", [True, False])
async def test_transparent(failure, monkeypatch, caplog_async):
    caplog_async.set_level("INFO")
    manager = MagicMock()

    if failure:
        monkeypatch.setattr(mitmproxy.platform, "original_addr", None)
    else:
        monkeypatch.setattr(
            mitmproxy.platform, "original_addr", lambda s: ("address", 42)
        )

    with taddons.context(Proxyserver()) as tctx:
        tctx.options.connection_strategy = "lazy"
        inst = ServerInstance.make("transparent@127.0.0.1:0", manager)
        await inst.start()
        await caplog_async.await_log("listening")

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
        assert await caplog_async.await_log("stopped")


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

    arch = platform.machine()
    if arch != "AMD64" and arch != "x86_64":
        return pytest.skip("Unsupported architecture for wg-test-client.")

    test_client_path = tdata.path(f"wg-test-client/{test_client_name}")
    test_conf = tdata.path(f"wg-test-client/test.conf")

    with taddons.context(Proxyserver()):
        inst = WireGuardServerInstance.make(f"wireguard:{test_conf}@0", MagicMock())

        await inst.start()
        assert "WireGuard server listening" in caplog.text

        _, port = inst.listen_addrs[0]

        assert inst.is_running
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
        assert "stopped" in caplog.text


async def test_wireguard_generate_conf(tmp_path):
    with taddons.context(Proxyserver()) as tctx:
        tctx.options.confdir = str(tmp_path)
        inst = WireGuardServerInstance.make(f"wireguard@0", MagicMock())
        assert not inst.client_conf()  # should not error.

        await inst.start()

        assert (tmp_path / "wireguard.conf").exists()
        assert inst.client_conf()
        assert inst.to_json()["wireguard_conf"]
        k = inst.server_key

        inst2 = WireGuardServerInstance.make(f"wireguard@0", MagicMock())
        await inst2.start()
        assert k == inst2.server_key

        await inst.stop()
        await inst2.stop()


async def test_wireguard_invalid_conf(tmp_path):
    with taddons.context(Proxyserver()):
        # directory instead of filename
        inst = WireGuardServerInstance.make(f"wireguard:{tmp_path}", MagicMock())

        with pytest.raises(ValueError, match="Invalid configuration file"):
            await inst.start()

        assert "Invalid configuration file" in repr(inst.last_exception)


async def test_tcp_start_error():
    manager = MagicMock()

    server = await asyncio.start_server(
        MagicMock(), host="127.0.0.1", port=0, reuse_address=False
    )
    port = server.sockets[0].getsockname()[1]

    with taddons.context() as tctx:
        inst = ServerInstance.make(f"regular@127.0.0.1:{port}", manager)
        with pytest.raises(
            OSError, match=f"proxy failed to listen on 127\\.0\\.0\\.1:{port}"
        ):
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
        assert await caplog_async.await_log("stopped")


async def test_udp_start_error():
    manager = MagicMock()

    with taddons.context():
        inst = ServerInstance.make("dns@127.0.0.1:0", manager)
        await inst.start()
        port = inst.listen_addrs[0][1]
        inst2 = ServerInstance.make(f"dns@127.0.0.1:{port}", manager)
        with pytest.raises(
            OSError, match=f"server failed to listen on 127\\.0\\.0\\.1:{port}"
        ):
            await inst2.start()
        await inst.stop()


async def test_udp_connection_reuse(monkeypatch):
    manager = MagicMock()
    manager.connections = {}

    monkeypatch.setattr(udp, "DatagramWriter", MagicMock())
    monkeypatch.setattr(DnsInstance, "handle_udp_connection", AsyncMock())

    with taddons.context():
        inst = cast(DnsInstance, ServerInstance.make("dns", manager))
        inst.handle_udp_datagram(
            MagicMock(), b"\x00\x00\x01", ("remoteaddr", 0), ("localaddr", 0)
        )
        inst.handle_udp_datagram(
            MagicMock(), b"\x00\x00\x02", ("remoteaddr", 0), ("localaddr", 0)
        )
        await asyncio.sleep(0)

        assert len(inst.manager.connections) == 1


async def test_udp_dual_stack(caplog_async):
    caplog_async.set_level("DEBUG")
    manager = MagicMock()
    manager.connections = {}

    with taddons.context():
        inst = ServerInstance.make("dns@:0", manager)
        await inst.start()
        assert await caplog_async.await_log("server listening")

        _, port, *_ = inst.listen_addrs[0]
        reader, writer = await udp.open_connection("127.0.0.1", port)
        writer.write(b"\x00\x00\x01")
        assert await caplog_async.await_log("sent an invalid message")
        writer.close()

        if "listening on IPv4 only" not in caplog_async.caplog.text:
            caplog_async.clear()
            reader, writer = await udp.open_connection("::1", port)
            writer.write(b"\x00\x00\x01")
            assert await caplog_async.await_log("sent an invalid message")
            writer.close()

        await inst.stop()
        assert await caplog_async.await_log("stopped")


@pytest.fixture()
def patched_local_redirector(monkeypatch):
    start_local_redirector = AsyncMock()
    monkeypatch.setattr(mitmproxy_rs, "start_local_redirector", start_local_redirector)
    # make sure _server and _instance are restored after this test
    monkeypatch.setattr(LocalRedirectorInstance, "_server", None)
    monkeypatch.setattr(LocalRedirectorInstance, "_instance", None)
    return start_local_redirector


async def test_local_redirector(patched_local_redirector, caplog_async):
    caplog_async.set_level("INFO")

    with taddons.context():
        inst = ServerInstance.make(f"local", MagicMock())
        assert not inst.is_running

        await inst.start()
        assert patched_local_redirector.called
        assert await caplog_async.await_log("Local redirector started.")
        assert inst.is_running

        await inst.stop()
        assert await caplog_async.await_log("Local redirector stopped")
        assert not inst.is_running

        # just called for coverage
        inst.make_top_layer(MagicMock())


async def test_local_redirector_startup_err(patched_local_redirector):
    patched_local_redirector.side_effect = RuntimeError(
        "Local redirector startup error"
    )

    with taddons.context():
        inst = ServerInstance.make(f"local:!curl", MagicMock())
        with pytest.raises(RuntimeError):
            await inst.start()
        assert not inst.is_running


async def test_multiple_local_redirectors(patched_local_redirector):
    manager = MagicMock()

    with taddons.context():
        inst1 = ServerInstance.make(f"local:curl", manager)
        await inst1.start()

        inst2 = ServerInstance.make(f"local:wget", manager)
        with pytest.raises(
            RuntimeError, match="Cannot spawn more than one local redirector"
        ):
            await inst2.start()


async def test_always_uses_current_instance(patched_local_redirector, monkeypatch):
    manager = MagicMock()

    with taddons.context():
        inst1 = ServerInstance.make(f"local:curl", manager)
        await inst1.start()
        await inst1.stop()

        handle_tcp, handle_udp = patched_local_redirector.await_args[0]

        inst2 = ServerInstance.make(f"local:wget", manager)
        await inst2.start()

        monkeypatch.setattr(inst2, "handle_tcp_connection", h_tcp := AsyncMock())
        await handle_tcp(Mock())
        assert h_tcp.await_count

        monkeypatch.setattr(inst2, "handle_udp_datagram", h_udp := Mock())
        handle_udp(Mock(), b"", ("", 0), ("", 0))
        assert h_udp.called
