import asyncio
import collections

from mitmproxy.connection import Client
from mitmproxy.connection import Server
from mitmproxy.proxy import commands
from mitmproxy.proxy import server
from mitmproxy.proxy import server_hooks


def test_server_connect_error(monkeypatch):
    monkeypatch.setattr(
        server.SimpleConnectionHandler, "__init__", mock_simple_connection_handler_init
    )
    monkeypatch.setattr(Client, "__init__", mock_client_init)
    s = server.SimpleConnectionHandler()

    monkeypatch.setattr(asyncio, "open_connection", mock_OSError)
    asyncio.run(s.open_connection(initialize_command()))

    assert server_hooks.ServerConnectErrorHook in server_hooks.all_hooks.values()


def mock_simple_connection_handler_init(self):
    self.client = Client()
    self.hook_handlers = {"server_connect_error": commands.StartHook.args}
    self.max_conns = collections.defaultdict(lambda: asyncio.Semaphore(5))


def mock_client_init(self):
    pass


def mock_OSError():
    raise OSError


def initialize_command() -> commands.OpenConnection:
    c = commands.OpenConnection(
        connection=Server(
            address="test address", transport_protocol="tcp", sockname="test sockname"
        )
    )
    return c
