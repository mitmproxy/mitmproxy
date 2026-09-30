import asyncio
import collections
import textwrap
from dataclasses import dataclass
from typing import Callable
from unittest import mock

import pytest

from mitmproxy import options
from mitmproxy.connection import Client
from mitmproxy.connection import ConnectionState
from mitmproxy.connection import Server
from mitmproxy.proxy import commands
from mitmproxy.proxy import layer
from mitmproxy.proxy import server
from mitmproxy.proxy import server_hooks
from mitmproxy.proxy.events import Event
from mitmproxy.proxy.events import HookCompleted
from mitmproxy.proxy.events import Start
from mitmproxy.proxy.mode_specs import ProxyMode


class MockConnectionHandler(server.SimpleConnectionHandler):
    hook_handlers: dict[str, mock.Mock | Callable]

    def __init__(self):
        super().__init__(
            reader=mock.Mock(),
            writer=mock.Mock(),
            options=options.Options(),
            mode=ProxyMode.parse("regular"),
            hook_handlers=collections.defaultdict(lambda: mock.Mock()),
        )


@pytest.mark.parametrize("result", ("success", "killed", "failed"))
async def test_open_connection(result, monkeypatch):
    handler = MockConnectionHandler()
    server_connect = handler.hook_handlers["server_connect"]
    server_connected = handler.hook_handlers["server_connected"]
    server_connect_error = handler.hook_handlers["server_connect_error"]
    server_disconnected = handler.hook_handlers["server_disconnected"]

    match result:
        case "success":
            monkeypatch.setattr(
                asyncio,
                "open_connection",
                mock.AsyncMock(return_value=(mock.MagicMock(), mock.MagicMock())),
            )
            monkeypatch.setattr(
                MockConnectionHandler, "handle_connection", mock.AsyncMock()
            )
        case "failed":
            monkeypatch.setattr(
                asyncio, "open_connection", mock.AsyncMock(side_effect=OSError)
            )
        case "killed":

            def _kill(d: server_hooks.ServerConnectionHookData) -> None:
                d.server.error = "do not connect"

            server_connect.side_effect = _kill

    await handler.open_connection(
        commands.OpenConnection(connection=Server(address=("server", 1234)))
    )

    assert server_connect.call_args[0][0].server.address == ("server", 1234)

    assert server_connected.called == (result == "success")
    assert server_connect_error.called == (result != "success")

    assert server_disconnected.called == (result == "success")


async def test_no_reentrancy(capsys):
    class ReentrancyTestLayer(layer.Layer):
        def handle_event(self, event: Event) -> layer.CommandGenerator[None]:
            if isinstance(event, Start):
                print("Starting...")
                yield FastHook()
                print("Start completed.")
            elif isinstance(event, HookCompleted):
                print(f"Hook completed (must not happen before start is completed).")

        def _handle_event(self, event: Event) -> layer.CommandGenerator[None]:
            raise NotImplementedError

    @dataclass
    class FastHook(commands.StartHook):
        pass

    handler = MockConnectionHandler()
    handler.layer = ReentrancyTestLayer(handler.layer.context)

    # This instead would fail: handler._server_event(Start())
    await handler.server_event(Start())
    await asyncio.sleep(0)

    assert capsys.readouterr().out == textwrap.dedent(
        """\
        Starting...
        Start completed.
        Hook completed (must not happen before start is completed).
        """
    )


async def test_handle_connection_waits_for_rust_stream_close(monkeypatch):
    class Stream:
        def __init__(self):
            self.closed = asyncio.Event()

        def close(self):
            pass

        async def wait_closed(self):
            await self.closed.wait()

    monkeypatch.setattr(server.mitmproxy_rs, "Stream", Stream)
    handler = MockConnectionHandler()
    handler.server_event = mock.AsyncMock()
    client = Client(
        peername=("127.0.0.1", 1234),
        sockname=("127.0.0.1", 4321),
        transport_protocol="udp",
        state=ConnectionState.OPEN,
    )
    writer = Stream()
    handler.transports[client] = server.ConnectionIO(
        reader=mock.AsyncMock(read=mock.AsyncMock(return_value=b"")), writer=writer
    )

    task = asyncio.create_task(handler.handle_connection(client))
    await asyncio.sleep(0.01)
    assert not task.done()
    writer.closed.set()
    await asyncio.wait_for(task, 1)
    assert client not in handler.transports
