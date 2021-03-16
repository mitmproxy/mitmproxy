"""
Commands make it possible for layers to communicate with the "outer world",
e.g. to perform IO or to ask the master.
A command is issued by a proxy layer and is then passed upwards to the proxy server, and from there
possibly to the master and addons.

The counterpart to commands are events.
"""
from typing import Literal, Union, TYPE_CHECKING

import mitmproxy.hooks
from mitmproxy.connection import Connection, Server

if TYPE_CHECKING:
    import mitmproxy.proxy.layer


class Command:
    """
    Base class for all commands
    """

    blocking: Union[bool, "mitmproxy.proxy.layer.Layer"] = False
    """
    Determines if the command blocks until it has been completed.
    For practical purposes, this attribute should be thought of as a boolean value,
    layers may swap out `True` with a reference to themselves to signal to outer layers
    that they do not need to block as well.

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

    def __init__(self, connection: Connection):
        self.connection = connection


class SendData(ConnectionCommand):
    """
    Send data to a remote peer
    """
    data: bytes

    def __init__(self, connection: Connection, data: bytes):
        super().__init__(connection)
        self.data = data

    def __repr__(self):
        target = str(self.connection).split("(", 1)[0].lower()
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
    half_close: bool
    """
    If True, only close our half of the connection by sending a FIN packet.
    This is required from some protocols which close their end to signal completion and then continue reading,
    for example HTTP/1.0 without Content-Length header.
    """

    def __init__(self, connection: Connection, half_close: bool = False):
        super().__init__(connection)
        self.half_close = half_close


class StartHook(Command, mitmproxy.hooks.Hook):
    """
    Start an event hook in the mitmproxy core.
    This triggers a particular function (derived from the class name) in all addons.
    """
    name = ""
    blocking = True

    def __new__(cls, *args, **kwargs):
        if cls is StartHook:
            raise TypeError("StartHook may not be instantiated directly.")
        return super().__new__(cls, *args, **kwargs)


class GetSocket(ConnectionCommand):
    """
    Get the underlying socket.
    This should really never be used, but is required to implement transparent mode.
    """
    blocking = True


class Log(Command):
    message: str
    level: str

    def __init__(self, message: str, level: Literal["error", "warn", "info", "alert", "debug"] = "info"):
        self.message = message
        self.level = level

    def __repr__(self):
        return f"Log({self.message!r}, {self.level!r})"
