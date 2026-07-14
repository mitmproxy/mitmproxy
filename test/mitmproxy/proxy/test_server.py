import asyncio
import collections
import textwrap
from dataclasses import dataclass
from typing import Callable
from unittest import mock

import pytest

from mitmproxy import options
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


async def test_handle_client_writer_close_oserror():
    """Test that handle_client handles OSError when closing writer."""
    handler = MockConnectionHandler()
    handler.client.error = "test error"

    # Set up a transport with a writer that raises OSError on close
    mock_writer = mock.Mock()
    mock_writer.close.side_effect = OSError("Connection reset")
    handler.transports[handler.client] = server.ConnectionIO(
        handler=None,
        reader=mock.Mock(),
        writer=mock_writer,
    )

    # Mock the hooks to avoid actual execution
    handler.handle_hook = mock.AsyncMock()

    # This should not raise an exception
    await handler.handle_client()

    # Verify writer.close() was called
    mock_writer.close.assert_called_once()


async def test_handle_connection_cleanup_with_oserror():
    """Test that handle_connection properly cleans up transports even when writer.close() raises OSError."""
    handler = MockConnectionHandler()

    # Create a mock connection
    connection = Server(address=("server", 1234))
    connection.state = 0  # ConnectionState.CLOSED

    # Set up a transport with a writer that raises OSError on close
    mock_writer = mock.Mock()
    mock_writer.close.side_effect = OSError("Connection reset")
    mock_reader = mock.AsyncMock()
    mock_reader.read.side_effect = OSError("Connection closed")

    handler.transports[connection] = server.ConnectionIO(
        handler=None,
        reader=mock_reader,
        writer=mock_writer,
    )

    # Mock the hooks to avoid actual execution
    handler.handle_hook = mock.AsyncMock()
    handler.server_event = mock.AsyncMock()

    # This should not raise an exception
    await handler.handle_connection(connection)

    # Verify writer.close() was called
    mock_writer.close.assert_called_once()
    # Verify transport was removed even though close() raised OSError
    assert connection not in handler.transports


async def test_handle_connection_cleanup_success():
    """Test that handle_connection properly cleans up transports on success path."""
    handler = MockConnectionHandler()

    # Create a mock connection
    connection = Server(address=("server", 1234))
    connection.state = 0  # ConnectionState.CLOSED

    # Set up a transport with a normal writer
    mock_writer = mock.Mock()
    mock_reader = mock.AsyncMock()
    mock_reader.read.side_effect = OSError("Connection closed")

    handler.transports[connection] = server.ConnectionIO(
        handler=None,
        reader=mock_reader,
        writer=mock_writer,
    )

    # Mock the hooks to avoid actual execution
    handler.handle_hook = mock.AsyncMock()
    handler.server_event = mock.AsyncMock()

    # This should complete successfully
    await handler.handle_connection(connection)

    # Verify writer.close() was called
    mock_writer.close.assert_called_once()
    # Verify transport was removed
    assert connection not in handler.transports
