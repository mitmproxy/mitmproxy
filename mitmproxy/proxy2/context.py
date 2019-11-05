from enum import Flag, auto
from typing import List, Optional, Sequence, Union

from mitmproxy.options import Options


class ConnectionState(Flag):
    CLOSED = 0
    CAN_READ = auto()
    CAN_WRITE = auto()
    OPEN = CAN_READ | CAN_WRITE


class Connection:
    """
    Connections exposed to the layers only contain metadata, no socket objects.
    """
    address: tuple
    state: ConnectionState
    tls: bool = False
    tls_established: bool = False
    alpn: Optional[bytes] = None
    alpn_offers: Sequence[bytes] = ()
    sni: Union[bytes, bool, None]

    @property
    def connected(self):
        return self.state is ConnectionState.OPEN

    def __repr__(self):
        return f"{type(self).__name__}({repr(self.__dict__)})"


class Client(Connection):
    sni: Optional[bytes] = None

    def __init__(self, address):
        self.address = address
        self.state = ConnectionState.OPEN


class Server(Connection):
    sni: Union[bytes, bool] = True
    """True: client SNI, False: no SNI, bytes: custom value"""
    address: Optional[tuple]

    def __init__(self, address: Optional[tuple]):
        self.address = address
        self.state = ConnectionState.CLOSED


class Context:
    """
    Layers get a context object that has all contextual information they require.
    """

    client: Client
    server: Server
    options: Options
    layers: List["mitmproxy.proxy2.layer.Layer"]

    def __init__(
            self,
            client: Client,
            options: Options,
    ) -> None:
        self.client = client
        self.options = options
        self.server = Server(None)
        self.layers = []
