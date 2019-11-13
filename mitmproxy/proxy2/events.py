"""
When IO actions occur at the proxy server, they are passed down to layers as events.
Events represent the only way for layers to receive new data from sockets.
The counterpart to events are commands.
"""
import socket
import typing

from mitmproxy.proxy2 import commands
from mitmproxy.proxy2.context import Connection


class Event:
    """
    Base class for all events.
    """

    def __repr__(self):
        return f"{type(self).__name__}({repr(self.__dict__)})"


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

    def __repr__(self):
        target = type(self.connection).__name__.lower()
        return f"DataReceived({target}, {self.data})"


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

    def __init_subclass__(cls, **kwargs):
        command_cls = cls.__annotations__["command"]
        if not issubclass(command_cls, commands.Command) and command_cls is not commands.Command:
            raise RuntimeError(f"{command_cls} needs a properly annotated command attribute.")
        command_reply_subclasses[command_cls] = cls


command_reply_subclasses: typing.Dict[commands.Command, typing.Type[CommandReply]] = {}


class OpenConnectionReply(CommandReply):
    command: commands.OpenConnection
    reply: typing.Optional[str]

    def __init__(
            self,
            command: commands.OpenConnection,
            err: typing.Optional[str]
    ):
        super().__init__(command, err)


class HookReply(CommandReply):
    command: commands.Hook

    def __init__(self, command: commands.Hook):
        super().__init__(command, None)

    def __repr__(self):
        return f"HookReply({repr(self.command)[5:-1]})"


class GetSocketReply(CommandReply):
    command: commands.GetSocket
    reply: socket.socket

    def __init__(
            self,
            command: commands.GetSocket,
            socket: socket.socket
    ):
        super().__init__(command, socket)
