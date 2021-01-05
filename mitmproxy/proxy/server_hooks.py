from dataclasses import dataclass

from . import commands, context


@dataclass
class ClientConnectedHook(commands.StartHook):
    """
    A client has connected to mitmproxy. Note that a connection can
    correspond to multiple HTTP requests.

    Setting client.error kills the connection.
    """
    client: context.Client


@dataclass
class ClientDisconnectedHook(commands.StartHook):
    """
    A client connection has been closed (either by us or the client).
    """
    blocking = False
    client: context.Client


@dataclass
class ServerConnectionHookData:
    server: context.Server
    client: context.Client


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
