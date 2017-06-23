"""
When IO actions occur at the proxy server, they are passed down to layers as events.
Events represent the only way for layers to receive new data from sockets.
The counterpart to events are commands.
"""
import typing

from mitmproxy.proxy.protocol2 import commands
from mitmproxy.proxy.protocol2.context import Connection


class Event:
    """
    Base class for all events.
    """

    def __repr__(self):
        return f"{type(self).__name__}({repr(self.__dict__)})"

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.__dict__ == other.__dict__
        return False


class Start(Event):
    """
    Every layer initially receives a start event.
    This is useful to emit events on startup.
    """
    pass


class ConnectionEvent(Event):
    """
    All events involving connection IO.
    """
    connection: Connection

    def __init__(self, connection: Connection):
        self.connection = connection


class ConnectionClosed(ConnectionEvent):
    """
    Remote has closed a connection.
    """
    pass


class DataReceived(ConnectionEvent):
    """
    Remote has sent some data.
    """

    def __init__(self, connection: Connection, data: bytes) -> None:
        super().__init__(connection)
        self.data = data


class ClientDataReceived(DataReceived):
    """
    Client has sent data.
    These subclasses simplify code for simple layers with one server and one client.
    """
    pass


class ServerDataReceived(DataReceived):
    pass


class CommandReply(Event):
    """
    Emitted when a command has been finished, e.g.
    when the master has replied or when we have established a server connection.
    """
    command: commands.Command
    reply: typing.Any

    def __init__(self, command: commands.Command, reply: typing.Any):
        self.command = command
        self.reply = reply

    def __new__(cls, *args, **kwargs):
        if cls is CommandReply:
            raise TypeError("CommandReply may not be instantiated directly.")
        return super().__new__(cls)


class OpenConnectionReply(CommandReply):
    command: commands.OpenConnection
    reply: str

    def __init__(self, command: commands.OpenConnection, ok: str):
        super().__init__(command, ok)


class HookReply(CommandReply):
    command: commands.Hook
    reply: typing.Any

    def __init__(self, command: commands.Hook, reply: typing.Any):
        super().__init__(command, reply)
