import asyncio
import collections
import textwrap
import threading
from dataclasses import dataclass
from typing import Callable
from unittest import mock

import pytest

from mitmproxy import options
from mitmproxy.connection import Server
from mitmproxy.proxy import commands
from mitmproxy.proxy import events
from mitmproxy.proxy import layer
from mitmproxy.proxy import server
from mitmproxy.proxy import server_hooks
from mitmproxy.proxy.events import Event
from mitmproxy.proxy.events import HookCompleted
from mitmproxy.proxy.events import Start
from mitmproxy.proxy.mode_specs import ProxyMode
from mitmproxy.script import run_in_thread


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


class AwaitCommandLayer(layer.Layer):
    def __init__(self, context, command):
        super().__init__(context)
        self.command = command
        self.completed = asyncio.Event()
        self.result = None

    def _handle_event(self, event: Event) -> layer.CommandGenerator[None]:
        if isinstance(event, Start):
            self.result = yield from self.command.unwrap()
            self.completed.set()


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


@pytest.mark.parametrize("outcome", ["result", "exception"])
async def test_await_completion(outcome):
    handler = MockConnectionHandler()
    handler.server_event = mock.AsyncMock()
    handler._drain_writers = mock.AsyncMock()

    async def awaitable():
        if outcome == "exception":
            raise RuntimeError("test error")
        return "result"

    command = commands.Await(awaitable())
    await handler.await_command(command)

    completed = handler.server_event.await_args.args[0]
    assert isinstance(completed, events.AwaitCompleted)
    assert completed.command is command
    if outcome == "result":
        assert completed.reply == ("result", None)
    else:
        assert completed.reply[0] is None
        assert isinstance(completed.reply[1], RuntimeError)


async def test_run_in_thread_does_not_block_other_connections():
    started = threading.Event()
    release = threading.Event()

    @run_in_thread
    def blocking():
        started.set()
        release.wait()
        return "slow"

    @run_in_thread
    def fast():
        return "fast"

    first = MockConnectionHandler()
    first.transports.clear()
    first_layer = AwaitCommandLayer(first.layer.context, commands.Await(blocking()))
    first.layer = first_layer

    second = MockConnectionHandler()
    second.transports.clear()
    second_layer = AwaitCommandLayer(second.layer.context, commands.Await(fast()))
    second.layer = second_layer

    try:
        await first.server_event(Start())
        async with asyncio.timeout(5):
            while not started.is_set():
                await asyncio.sleep(0.01)

        await second.server_event(Start())
        await asyncio.wait_for(second_layer.completed.wait(), timeout=5)

        assert second_layer.result == "fast"
        assert not first_layer.completed.is_set()
    finally:
        release.set()

    await asyncio.wait_for(first_layer.completed.wait(), timeout=5)
    assert first_layer.result == "slow"
