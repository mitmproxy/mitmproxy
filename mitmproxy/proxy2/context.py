from typing import Optional, List, Union

from mitmproxy.options import Options


class Connection:
    """
    Connections exposed to the layers only contain metadata, no socket objects.
    """
    address: tuple
    connected: bool = False
    tls: bool = False
    alpn: Optional[bytes] = None

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

    def __init__(self, address):
        self.address = address


class Context:
    """
    Layers get a context object that has all contextual information they require.
    """

    client: Client
    server: Optional[Server]
    options: Options
    layers: List["mitmproxy.proxy2.layer.Layer"]

    def __init__(
            self,
            client: Client,
            server: Optional[Server],
            options: Options,
    ) -> None:
        self.client = client
        self.server = server
        self.options = options
        self.layers = []
