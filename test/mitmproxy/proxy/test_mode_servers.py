import asyncio
import platform
import socket
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import Mock

import pytest

from ...conftest import no_ipv6
from ...conftest import skip_not_linux
import mitmproxy.platform
import mitmproxy_rs
from mitmproxy.addons.proxyserver import Proxyserver
from mitmproxy.proxy.mode_servers import LocalRedirectorInstance
from mitmproxy.proxy.mode_servers import ServerInstance
from mitmproxy.proxy.mode_servers import TunInstance
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


async def _echo_server(self: ConnectionHandler):
    t = self.transports[self.client]
    data = await t.reader.read(65535)
    t.writer.write(data.upper())
    await t.writer.drain()
    t.writer.close()


async def test_wireguard(tdata, monkeypatch, caplog):
    caplog.set_level("DEBUG")

    monkeypatch.setattr(ConnectionHandler, "handle_client", _echo_server)

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


@pytest.mark.parametrize("host", ["127.0.0.1", "::1"])
async def test_wireguard_dual_stack(host, caplog_async):
    caplog_async.set_level("DEBUG")

    system = platform.system()
    if system not in ("Linux", "Darwin", "Windows"):
        return pytest.skip("Unsupported platform for wg-test-client.")

    arch = platform.machine()
    if arch != "AMD64" and arch != "x86_64":
        return pytest.skip("Unsupported architecture for wg-test-client.")

    with taddons.context(Proxyserver()):
        inst = WireGuardServerInstance.make(f"wireguard@0", MagicMock())

        await inst.start()
        assert await caplog_async.await_log("WireGuard server listening")

        _, port = inst.listen_addrs[0]

        assert inst.is_running

        stream = await mitmproxy_rs.udp.open_udp_connection(host, port)
        stream.write(b"\x00\x00\x01")
        assert await caplog_async.await_log("Received invalid WireGuard packet")
        stream.close()
        await stream.wait_closed()

        await inst.stop()
        assert await caplog_async.await_log("stopped")


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
        stream = await mitmproxy_rs.udp.open_udp_connection(host, port)

        stream.write(b"\x00\x00\x01")
        assert await caplog_async.await_log("sent an invalid message")

        stream.close()
        await stream.wait_closed()

        await inst.stop()
        assert await caplog_async.await_log("stopped")


async def test_udp_start_error():
    manager = MagicMock()

    with taddons.context():
        inst = ServerInstance.make("reverse:udp://127.0.0.1:1234@127.0.0.1:0", manager)
        await inst.start()
        port = inst.listen_addrs[0][1]
        inst2 = ServerInstance.make(
            f"reverse:udp://127.0.0.1:1234@127.0.0.1:{port}", manager
        )
        with pytest.raises(
            Exception, match=f"Failed to bind UDP socket to 127.0.0.1:{port}"
        ):
            await inst2.start()
        await inst.stop()


@pytest.mark.parametrize("ip_version", ["v4", "v6"])
@pytest.mark.parametrize("protocol", ["tcp", "udp"])
async def test_dual_stack(ip_version, protocol, caplog_async):
    """Test that a server bound to "" binds on both IPv4 and IPv6 for both TCP and UDP."""

    if ip_version == "v6" and no_ipv6:
        pytest.skip("Skipped because IPv6 is unavailable.")

    if ip_version == "v4":
        addr = "127.0.0.1"
    else:
        addr = "::1"

    caplog_async.set_level("DEBUG")
    manager = MagicMock()
    manager.connections = {}

    with taddons.context():
        inst = ServerInstance.make("dns@0", manager)
        await inst.start()
        assert await caplog_async.await_log("server listening")
        _, port, *_ = inst.listen_addrs[0]

        if protocol == "tcp":
            _, stream = await asyncio.open_connection(addr, port)
        else:
            stream = await mitmproxy_rs.udp.open_udp_connection(addr, port)
        stream.write(b"\x00\x00\x01")
        assert await caplog_async.await_log("sent an invalid message")
        stream.close()
        await stream.wait_closed()

        await inst.stop()
        assert await caplog_async.await_log("stopped")


@pytest.mark.parametrize("transport_protocol", ["udp", "tcp"])
async def test_dns_start_stop(caplog_async, transport_protocol):
    caplog_async.set_level("INFO")
    manager = MagicMock()
    manager.connections = {}

    with taddons.context():
        inst = ServerInstance.make("dns@127.0.0.1:0", manager)
        await inst.start()
        assert await caplog_async.await_log("server listening")

        host, port, *_ = inst.listen_addrs[0]
        if transport_protocol == "tcp":
            _, stream = await asyncio.open_connection("127.0.0.1", port)
        elif transport_protocol == "udp":
            stream = await mitmproxy_rs.udp.open_udp_connection("127.0.0.1", port)

        stream.write(b"\x00\x00\x01")
        assert await caplog_async.await_log("sent an invalid message")

        stream.close()
        await stream.wait_closed()

        await inst.stop()
        assert await caplog_async.await_log("stopped")


@skip_not_linux
async def test_tun_mode(monkeypatch, caplog):
    monkeypatch.setattr(ConnectionHandler, "handle_client", _echo_server)

    with taddons.context(Proxyserver()):
        inst = TunInstance.make(f"tun", MagicMock())
        assert inst.tun_name is None
        try:
            await inst.start()
        except RuntimeError as e:
            if "Operation not permitted" in str(e):
                return pytest.skip("tun mode test must be run as root")
            raise
        assert inst.tun_name
        assert inst.is_running
        assert "tun_name" in inst.to_json()

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BINDTODEVICE, inst.tun_name.encode())
        await asyncio.get_running_loop().sock_connect(s, ("192.0.2.1", 1234))
        reader, writer = await asyncio.open_connection(sock=s)
        writer.write(b"hello")
        await writer.drain()
        assert await reader.readexactly(5) == b"HELLO"
        writer.close()
        await writer.wait_closed()
        await inst.stop()


async def test_tun_mode_mocked(monkeypatch):
    tun_interface = Mock()
    tun_interface.tun_name = lambda: "tun0"
    tun_interface.wait_closed = AsyncMock()
    create_tun_interface = AsyncMock(return_value=tun_interface)
    monkeypatch.setattr(mitmproxy_rs.tun, "create_tun_interface", create_tun_interface)

    inst = TunInstance.make(f"tun", MagicMock())
    assert not inst.is_running
    assert inst.tun_name is None

    await inst.start()
    assert inst.is_running
    assert inst.tun_name == "tun0"
    assert inst.to_json()["tun_name"] == "tun0"

    await inst.stop()
    assert not inst.is_running
    assert inst.tun_name is None


@pytest.fixture()
def patched_local_redirector(monkeypatch):
    start_local_redirector = AsyncMock(return_value=Mock())
    monkeypatch.setattr(
        mitmproxy_rs.local, "start_local_redirector", start_local_redirector
    )
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
        inst1 = LocalRedirectorInstance.make(f"local:curl", manager)
        await inst1.start()
        await inst1.stop()

        handle_stream, _ = patched_local_redirector.await_args[0]

        inst2 = LocalRedirectorInstance.make(f"local:wget", manager)
        await inst2.start()

        monkeypatch.setattr(inst2, "handle_stream", handler := AsyncMock())
        await handle_stream(Mock())
        assert handler.await_count
