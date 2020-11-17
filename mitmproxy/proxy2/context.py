import warnings
from enum import Flag, auto
from typing import List, Literal, Optional, Sequence, Tuple, Union

from mitmproxy import certs
from mitmproxy.net import server_spec
from mitmproxy.options import Options


class ConnectionState(Flag):
    CLOSED = 0
    CAN_READ = auto()
    CAN_WRITE = auto()
    OPEN = CAN_READ | CAN_WRITE


# practically speaking we may have IPv6 addresses with flowinfo and scope_id,
# but type checking isn't good enough to properly handle tuple unions.
# this version at least provides useful type checking messages.
Address = Tuple[str, int]


class Connection:
    """
    Connections exposed to the layers only contain metadata, no socket objects.
    """
    state: ConnectionState
    peername: Optional[Address]
    sockname: Optional[Address]
    error: Optional[str] = None

    tls: bool = False
    certificate_list: Optional[Sequence[certs.Cert]] = None
    """
    The TLS certificate list as sent by the peer. 
    The first certificate is the end-entity certificate.
    
    [RFC 8446] Prior to TLS 1.3, "certificate_list" ordering required each
    certificate to certify the one immediately preceding it; however,
    some implementations allowed some flexibility.  Servers sometimes
    send both a current and deprecated intermediate for transitional
    purposes, and others are simply configured incorrectly, but these
    cases can nonetheless be validated properly.  For maximum
    compatibility, all implementations SHOULD be prepared to handle
    potentially extraneous certificates and arbitrary orderings from any
    TLS version, with the exception of the end-entity certificate which
    MUST be first.
    """
    alpn: Optional[bytes] = None
    alpn_offers: Sequence[bytes] = ()

    # we may want to add SSL_CIPHER_description here, but that's currently not exposed by cryptography
    cipher: Optional[str] = None
    """The active cipher name as returned by OpenSSL's SSL_CIPHER_get_name"""
    cipher_list: Sequence[str] = ()
    """Ciphers accepted by the proxy server."""
    tls_version: Optional[str] = None
    sni: Union[bytes, Literal[True], None]

    timestamp_end: Optional[float] = None
    """Connection end timestamp"""
    timestamp_tls_setup: Optional[float] = None
    """TLS session established."""

    @property
    def connected(self):
        return self.state is ConnectionState.OPEN

    @property
    def tls_established(self) -> bool:
        return self.timestamp_tls_setup is not None

    def __repr__(self):
        attrs = repr({
            k: {"cipher_list": lambda: f"<{len(v)} ciphers>"}.get(k, lambda: v)()
            for k, v in self.__dict__.items()
        })
        return f"{type(self).__name__}({attrs})"

    @property
    def alpn_proto_negotiated(self) -> bytes:
        warnings.warn("Server.alpn_proto_negotiated is deprecated, use Server.alpn instead.", PendingDeprecationWarning)
        return self.alpn


class Client(Connection):
    state = ConnectionState.OPEN
    peername: Address
    sockname: Address

    timestamp_start: float
    """TCP SYN received"""

    sni: Union[bytes, None] = None

    def __init__(self, peername, sockname, timestamp_start):
        self.peername = peername
        self.sockname = sockname
        self.timestamp_start = timestamp_start

    @property
    def address(self):
        warnings.warn("Client.address is deprecated, use Client.peername instead.", PendingDeprecationWarning)
        return self.peername

    @property
    def cipher_name(self) -> Optional[str]:
        warnings.warn("Client.cipher_name is deprecated, use Client.cipher instead.", PendingDeprecationWarning)
        return self.cipher


class Server(Connection):
    state = ConnectionState.CLOSED
    peername = None
    sockname = None
    address: Optional[Address]

    timestamp_start: Optional[float] = None
    """TCP SYN sent"""
    timestamp_tcp_setup: Optional[float] = None
    """TCP ACK received"""

    sni = True
    """True: client SNI, False: no SNI, bytes: custom value"""
    via: Optional[server_spec.ServerSpec] = None

    def __init__(self, address: Optional[tuple]):
        self.address = address

    @property
    def ip_address(self) -> Address:
        warnings.warn("Server.ip_address is deprecated, use Server.peername instead.", PendingDeprecationWarning)
        return self.peername

    @property
    def cert(self) -> Optional[certs.Cert]:
        warnings.warn("Server.alpn_proto_negotiated is deprecated, use Server.alpn instead.", PendingDeprecationWarning)
        if self.certificate_list:
            return self.certificate_list[0]
        else:
            return None


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
