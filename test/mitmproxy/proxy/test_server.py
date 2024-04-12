import asyncio
import collections

from mitmproxy.connection import Client
from mitmproxy.connection import Server
from mitmproxy.proxy import commands
from mitmproxy.proxy import server
from mitmproxy.proxy import server_hooks


def initialize_command() -> commands.OpenConnection:
    c = commands.OpenConnection(
        connection=Server(
            address=("server", 5678), transport_protocol="tcp", sockname="test sockname"
        )
    )
    return c

def server_connect_error_cb(hook_data: server_hooks.ServerConnectionHookData):
    global hook_triggered
    hook_triggered = True

def mock_simple_connection_handler_init(self):
    self.client = Client(peername=("client", 1234), sockname=("server", 5678))
    self.hook_handlers = {
        server_hooks.ServerConnectErrorHook.name: server_connect_error_cb
        }
    self.max_conns = collections.defaultdict(lambda: asyncio.Semaphore(5))
    self.timeout_watchdog = server.TimeoutWatchdog(0, lambda x: None)

def test_server_connect_error(monkeypatch):
    global hook_triggered
    hook_triggered = False

    monkeypatch.setattr(
        server.SimpleConnectionHandler, "__init__", mock_simple_connection_handler_init
    )
    
    s = server.SimpleConnectionHandler()
    asyncio.run(s.open_connection(initialize_command()))
    
    assert hook_triggered
