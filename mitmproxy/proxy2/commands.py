"""
Commands make it possible for layers to communicate with the "outer world",
e.g. to perform IO or to ask the master.
A command is issued by a proxy layer and is then passed upwards to the proxy server, and from there
possibly to the master and addons.

The counterpart to commands are events.
"""
import typing

from mitmproxy.proxy2.context import Connection, Server


class Command:
    """
    Base class for all commands
    """

    blocking: bool = False
    """
    Determines if the command blocks until it has been completed.

    Example:

        reply = yield Hook("requestheaders", flow)  # blocking command
        yield Log("hello world", "info")            # non-blocking
    """

    def __repr__(self):
        x = self.__dict__.copy()
        x.pop("blocking", None)
        return f"{type(self).__name__}({repr(x)})"


class ConnectionCommand(Command):
    """
    Commands involving a specific connection
    """
    connection: Connection

    def __init__(self, connection: Connection) -> None:
        self.connection = connection


class SendData(ConnectionCommand):
    """
    Send data to a remote peer
    """
    data: bytes

    def __init__(self, connection: Connection, data: bytes) -> None:
        super().__init__(connection)
        self.data = data

    def __repr__(self):
        target = type(self.connection).__name__.lower()
        return f"SendData({target}, {self.data})"


class OpenConnection(ConnectionCommand):
    """
    Open a new connection
    """
    connection: Server
    blocking = True


class CloseConnection(ConnectionCommand):
    """
    Close a connection. If the client connection is closed,
    all other connections will ultimately be closed during cleanup.
    """


class Hook(Command):
    """
    Callback to the master (like ".ask()")
    """
    blocking = True
    name: str
    data: typing.Any

    def __init__(self, name: str, data: typing.Any) -> None:
        self.name = name
        self.data = data

    def __repr__(self):
        return f"Hook({self.name})"
        # data = repr(self.data).replace("\r\n", " ")
        # return f"Hook({self.name}: {data})"


class GetSocket(ConnectionCommand):
    """
    Get the underlying socket.
    This should really never be used, but is required to implement transparent mode.
    """
    blocking = True


class Log(Command):
    message: str
    level: str

    def __init__(self, message: str, level: str="info"):
        self.message = message
        self.level = level

    def __repr__(self):
        return f"Log({self.message}, {self.level})"


TCommandGenerator = typing.Generator[Command, typing.Any, None]
