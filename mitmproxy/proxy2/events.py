"""
When IO actions occur at the proxy server, they are passed down to layers as events.
Events represent the only way for layers to receive new data from sockets.
The counterpart to events are commands.
"""
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


class CommandReply(Event):
    """
    Emitted when a command has been finished, e.g.
    when the master has replied or when we have established a server connection.
    """
    command: typing.Union[commands.Command, int]
    reply: typing.Any

    def __init__(self, command: typing.Union[commands.Command, int], reply: typing.Any):
        self.command = command
        self.reply = reply

    def __new__(cls, *args, **kwargs):
        if cls is CommandReply:
            raise TypeError("CommandReply may not be instantiated directly.")
        return super().__new__(cls)


class OpenConnectionReply(CommandReply):
    command: typing.Union[commands.OpenConnection, int]
    reply: str

    def __init__(
            self,
            command: typing.Union[commands.OpenConnection, int],
            err: typing.Optional[str]
    ):
        super().__init__(command, err)


class HookReply(CommandReply):
    command: typing.Union[commands.Hook, int]
    reply: typing.Any

    def __init__(self, command: typing.Union[commands.Hook, int], reply: typing.Any):
        super().__init__(command, reply)
