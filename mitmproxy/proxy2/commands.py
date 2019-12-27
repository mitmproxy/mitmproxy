"""
Commands make it possible for layers to communicate with the "outer world",
e.g. to perform IO or to ask the master.
A command is issued by a proxy layer and is then passed upwards to the proxy server, and from there
possibly to the master and addons.

The counterpart to commands are events.
"""
import dataclasses
import re
import typing

from mitmproxy.proxy2.context import Connection, Server


class Command:
    """
    Base class for all commands
    """

    blocking: typing.ClassVar[bool] = False
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


class Hook(Command):
    """
    Callback to the master (like ".ask()")
    """
    blocking = True
    name: typing.ClassVar[str]

    def __new__(cls, *args, **kwargs):
        if cls is Hook:
            raise TypeError("Hook may not be instantiated directly.")
        return super().__new__(cls)

    def __init_subclass__(cls, **kwargs):
        # initialize .name attribute.
        if not getattr(cls, "name", None):
            cls.name = re.sub('(?!^)([A-Z]+)', r'_\1', cls.__name__.replace("Hook", "")).lower()
        if cls.name in all_hooks:
            other = all_hooks[cls.name]
            raise RuntimeError(f"Two conflicting hooks for {cls.name}: {cls} and {other}")
        all_hooks[cls.name] = cls

        # a bit hacky: add a default constructor.
        dataclasses.dataclass(cls, repr=False, eq=False)

    def __repr__(self):
        return f"Hook({self.name})"

    def as_tuple(self) -> typing.List[typing.Any]:
        args = []
        # noinspection PyDataclass
        for field in dataclasses.fields(self):
            args.append(getattr(self, field.name))
        return args


all_hooks: typing.Dict[str, typing.Type[Hook]] = {}


# TODO: Move descriptions from addons/events.py into hooks and have hook documentation generated from all_hooks.


class GetSocket(ConnectionCommand):
    """
    Get the underlying socket.
    This should really never be used, but is required to implement transparent mode.
    """
    blocking = True


class Log(Command):
    message: str
    level: str

    def __init__(self, message: str, level: str = "info"):
        self.message = message
        self.level = level

    def __repr__(self):
        return f"Log({self.message}, {self.level})"
