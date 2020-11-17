from dataclasses import dataclass

from . import commands, context


class ClientConnectedHook(commands.Hook):
    """
    A client has connected to mitmproxy. Note that a connection can
    correspond to multiple HTTP requests.

    Setting client.error kills the connection.
    """
    client: context.Client


class ClientClosedHook(commands.Hook):
    """
    A client connection has been closed (either by us or the client).
    """
    blocking = False
    client: context.Client


@dataclass
class ServerConnectionHookData:
    server: context.Server
    client: context.Client


class ServerConnectHook(commands.Hook):
    """
    Mitmproxy is about to connect to a server.
    Note that a connection can correspond to multiple requests.

    Setting data.server.error kills the connection.
    """
    data: ServerConnectionHookData


class ServerConnectedHook(commands.Hook):
    """
    Mitmproxy has connected to a server.
    """
    blocking = False
    data: ServerConnectionHookData


class ServerClosedHook(commands.Hook):
    """
    A server connection has been closed (either by us or the server).
    """
    blocking = False
    data: ServerConnectionHookData
