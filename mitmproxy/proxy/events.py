"""
When IO actions occur at the proxy server, they are passed down to layers as events.
Events represent the only way for layers to receive new data from sockets.
The counterpart to events are commands.
"""

import typing
import warnings
from dataclasses import dataclass
from dataclasses import is_dataclass
from typing import Any
from typing import Generic
from typing import TypeVar

from mitmproxy import flow
from mitmproxy.connection import Connection
from mitmproxy.proxy import commands


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


@dataclass
class ConnectionEvent(Event):
    """
    All events involving connection IO.
    """

    connection: Connection


@dataclass
class DataReceived(ConnectionEvent):
    """
    Remote has sent some data.
    """

    data: bytes

    def __repr__(self):
        target = type(self.connection).__name__.lower()
        return f"DataReceived({target}, {self.data!r})"


class ConnectionClosed(ConnectionEvent):
    """
    Remote has closed a connection.
    """


class CommandCompleted(Event):
    """
    Emitted when a command has been finished, e.g.
    when the master has replied or when we have established a server connection.
    """

    command: commands.Command
    reply: Any

    def __new__(cls, *args, **kwargs):
        if cls is CommandCompleted:
            raise TypeError("CommandCompleted may not be instantiated directly.")
        assert is_dataclass(cls)
        return super().__new__(cls)

    def __init_subclass__(cls, **kwargs):
        command_cls = typing.get_type_hints(cls).get("command", None)
        valid_command_subclass = (
            isinstance(command_cls, type)
            and issubclass(command_cls, commands.Command)
            and command_cls is not commands.Command
        )
        if not valid_command_subclass:
            warnings.warn(
                f"{cls} needs a properly annotated command attribute.",
                RuntimeWarning,
            )
        if command_cls in command_reply_subclasses:
            other = command_reply_subclasses[command_cls]
            warnings.warn(
                f"Two conflicting subclasses for {command_cls}: {cls} and {other}",
                RuntimeWarning,
            )
        command_reply_subclasses[command_cls] = cls

    def __repr__(self):
        return f"Reply({repr(self.command)}, {repr(self.reply)})"


command_reply_subclasses: dict[commands.Command, type[CommandCompleted]] = {}


@dataclass(repr=False)
class OpenConnectionCompleted(CommandCompleted):
    command: commands.OpenConnection
    reply: str | None
    """error message"""


@dataclass(repr=False)
class HookCompleted(CommandCompleted):
    command: commands.StartHook
    reply: None = None


T = TypeVar("T")


@dataclass
class MessageInjected(Event, Generic[T]):
    """
    The user has injected a custom WebSocket/TCP/... message.
    """

    flow: flow.Flow
    message: T


@dataclass
class Wakeup(CommandCompleted):
    """
    Event sent to layers that requested a wakeup using RequestWakeup.
    """

    command: commands.RequestWakeup
