"""
The only way for layers to do IO is to emit events indicating what should be done.
For example, a layer may first emit a OpenConnection event and then a SendData event.
Likewise, layers only receive IO via events.
"""
from typing import Generator, Any

from mitmproxy.proxy.protocol2.context import Connection


class Event:
    def __repr__(self):
        return "{}({})".format(type(self).__name__, repr(self.__dict__))


TEventGenerator = Generator[Event, Any, None]


class Start(Event):
    """
    Every layer initially receives a start event.
    This is useful to emit events on startup, which otherwise would not be possible.
    """
    pass


class ConnectionEvent(Event):
    """
    All events involving IO connections.
    """

    def __init__(self, connection: Connection):
        self.connection = connection


class OpenConnection(ConnectionEvent):
    pass


class CloseConnection(ConnectionEvent):
    """
    (this would be send by proxy and by layers. keep it that way?)
    """
    pass


class SendData(ConnectionEvent):
    def __init__(self, connection: Connection, data: bytes) -> None:
        super().__init__(connection)
        self.data = data


class ReceiveData(ConnectionEvent):
    def __init__(self, connection: Connection, data: bytes) -> None:
        super().__init__(connection)
        self.data = data
