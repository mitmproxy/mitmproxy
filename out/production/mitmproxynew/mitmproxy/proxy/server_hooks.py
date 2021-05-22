from dataclasses import dataclass

from mitmproxy import connection
from . import commands


@dataclass
class ClientConnectedHook(commands.StartHook):
    """
    A client has connected to mitmproxy. Note that a connection can
    correspond to multiple HTTP requests.

    Setting client.error kills the connection.
    """
    client: connection.Client


@dataclass
class ClientDisconnectedHook(commands.StartHook):
    """
    A client connection has been closed (either by us or the client).
    """
    blocking = False
    client: connection.Client


@dataclass
class ServerConnectionHookData:
    """Event data for server connection event hooks."""

    server: connection.Server
    """The server connection this hook is about."""
    client: connection.Client
    """The client on the other end."""


@dataclass
class ServerConnectHook(commands.StartHook):
    """
    Mitmproxy is about to connect to a server.
    Note that a connection can correspond to multiple requests.

    Setting data.server.error kills the connection.
    """
    data: ServerConnectionHookData


@dataclass
class ServerConnectedHook(commands.StartHook):
    """
    Mitmproxy has connected to a server.
    """
    blocking = False
    data: ServerConnectionHookData


@dataclass
class ServerDisconnectedHook(commands.StartHook):
    """
    A server connection has been closed (either by us or the server).
    """
    blocking = False
    data: ServerConnectionHookData
