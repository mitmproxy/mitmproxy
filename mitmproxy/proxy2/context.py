from enum import Flag, auto
from typing import List, Literal, Optional, Sequence, Union

from mitmproxy import certs
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
    address: Optional[tuple]
    state: ConnectionState
    tls: bool = False
    tls_established: bool = False
    certificate_chain: Optional[Sequence[certs.Cert]] = None
    alpn: Optional[bytes] = None
    alpn_offers: Sequence[bytes] = ()
    cipher_list: Sequence[bytes] = ()
    tls_version: Optional[str] = None
    sni: Union[bytes, Literal[True], None]

    timestamp_tls_setup: Optional[float] = None

    @property
    def connected(self):
        return self.state is ConnectionState.OPEN

    def __repr__(self):
        attrs = repr({
            k: {"cipher_list": lambda: f"<{len(v)} ciphers>"}.get(k,lambda: v)()
            for k, v in self.__dict__.items()
        })
        return f"{type(self).__name__}({attrs})"


class Client(Connection):
    sni: Union[bytes, None] = None
    address: tuple

    def __init__(self, address):
        self.address = address
        self.state = ConnectionState.OPEN


class Server(Connection):
    sni = True
    """True: client SNI, False: no SNI, bytes: custom value"""
    via: Optional["Server"] = None

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

    def fork(self) -> "Context":
        ret = Context(self.client, self.options)
        ret.server = self.server
        ret.layers = self.layers.copy()
        return ret
