from typing import Optional, List, Union, Sequence

from mitmproxy.options import Options


class Connection:
    """
    Connections exposed to the layers only contain metadata, no socket objects.
    """
    address: tuple
    connected: bool = False
    tls: bool = False
    tls_established: bool = False
    alpn: Optional[bytes] = None
    alpn_offers: Sequence[bytes] = ()

    def __repr__(self):
        return f"{type(self).__name__}({repr(self.__dict__)})"


class Client(Connection):
    sni: Optional[bytes] = None

    def __init__(self, address):
        self.address = address
        self.connected = True


class Server(Connection):
    sni: Union[bytes, bool] = True
    """True: client SNI, False: no SNI, bytes: custom value"""
    address: Optional[tuple]

    def __init__(self, address: Optional[tuple]):
        self.address = address


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
