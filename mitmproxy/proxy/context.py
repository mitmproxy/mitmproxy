import uuid
import warnings
from abc import ABCMeta
from enum import Flag
from typing import List, Literal, Optional, Sequence, Tuple, Union, TYPE_CHECKING

from mitmproxy import certs
from mitmproxy.coretypes import serializable
from mitmproxy.net import server_spec
from mitmproxy.options import Options

if TYPE_CHECKING:
    import mitmproxy.proxy.layer


class ConnectionState(Flag):
    CLOSED = 0
    CAN_READ = 1
    CAN_WRITE = 2
    OPEN = CAN_READ | CAN_WRITE


# practically speaking we may have IPv6 addresses with flowinfo and scope_id,
# but type checking isn't good enough to properly handle tuple unions.
# this version at least provides useful type checking messages.
Address = Tuple[str, int]


class Connection(serializable.Serializable, metaclass=ABCMeta):
    """
    Connections exposed to the layers only contain metadata, no socket objects.
    """
    # all connections have a unique id. While
    # f.client_conn == f2.client_conn already holds true for live flows (where we have object identity),
    # we also want these semantics for recorded flows.
    id: str
    state: ConnectionState
    peername: Optional[Address]
    sockname: Optional[Address]
    error: Optional[str] = None

    tls: bool = False
    certificate_list: Sequence[certs.Cert] = ()
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

    def __eq__(self, other):
        if isinstance(other, Connection):
            return self.id == other.id
        return False

    def __hash__(self):
        return hash(self.id)

    def __repr__(self):
        attrs = repr({
            k: {"cipher_list": lambda: f"<{len(v)} ciphers>"}.get(k, lambda: v)()
            for k, v in self.__dict__.items()
        })
        return f"{type(self).__name__}({attrs})"

    @property
    def alpn_proto_negotiated(self) -> Optional[bytes]:  # pragma: no cover
        warnings.warn("Server.alpn_proto_negotiated is deprecated, use Server.alpn instead.", DeprecationWarning)
        return self.alpn


class Client(Connection):
    state: ConnectionState = ConnectionState.OPEN
    peername: Address
    sockname: Address

    timestamp_start: float
    """TCP SYN received"""

    sni: Union[bytes, None] = None

    def __init__(self, peername, sockname, timestamp_start):
        self.id = str(uuid.uuid4())
        self.peername = peername
        self.sockname = sockname
        self.timestamp_start = timestamp_start

    def get_state(self):
        # Important: Retain full compatibility with old proxy core for now!
        # This means we need to add all new fields to the old implementation.
        return {
            'address': self.peername,
            'alpn_proto_negotiated': self.alpn,
            'cipher_name': self.cipher,
            'id': self.id,
            'mitmcert': None,
            'sni': self.sni,
            'timestamp_end': self.timestamp_end,
            'timestamp_start': self.timestamp_start,
            'timestamp_tls_setup': self.timestamp_tls_setup,
            'tls_established': self.tls_established,
            'tls_extensions': [],
            'tls_version': self.tls_version,
            # only used in sans-io
            'state': self.state.value,
            'sockname': self.sockname,
            'error': self.error,
            'tls': self.tls,
            'certificate_list': [x.get_state() for x in self.certificate_list],
            'alpn_offers': self.alpn_offers,
            'cipher_list': self.cipher_list,
        }

    @classmethod
    def from_state(cls, state) -> "Client":
        client = Client(
            state["address"],
            ("mitmproxy", 8080),
            state["timestamp_start"]
        )
        client.set_state(state)
        return client

    def set_state(self, state):
        self.peername = tuple(state["address"]) if state["address"] else None
        self.alpn = state["alpn_proto_negotiated"]
        self.cipher = state["cipher_name"]
        self.id = state["id"]
        self.sni = state["sni"]
        self.timestamp_end = state["timestamp_end"]
        self.timestamp_start = state["timestamp_start"]
        self.timestamp_tls_setup = state["timestamp_tls_setup"]
        self.tls_version = state["tls_version"]
        # only used in sans-io
        self.state = ConnectionState(state["state"])
        self.sockname = tuple(state["sockname"]) if state["sockname"] else None
        self.error = state["error"]
        self.tls = state["tls"]
        self.certificate_list = [certs.Cert.from_state(x) for x in state["certificate_list"]]
        self.alpn_offers = state["alpn_offers"]
        self.cipher_list = state["cipher_list"]

    @property
    def address(self):  # pragma: no cover
        warnings.warn("Client.address is deprecated, use Client.peername instead.", DeprecationWarning, stacklevel=2)
        return self.peername

    @address.setter
    def address(self, x):  # pragma: no cover
        warnings.warn("Client.address is deprecated, use Client.peername instead.", DeprecationWarning, stacklevel=2)
        self.peername = x

    @property
    def cipher_name(self) -> Optional[str]:  # pragma: no cover
        warnings.warn("Client.cipher_name is deprecated, use Client.cipher instead.", DeprecationWarning, stacklevel=2)
        return self.cipher

    @property
    def clientcert(self) -> Optional[certs.Cert]:  # pragma: no cover
        warnings.warn("Client.clientcert is deprecated, use Client.certificate_list instead.", DeprecationWarning, stacklevel=2)
        if self.certificate_list:
            return self.certificate_list[0]
        else:
            return None

    @clientcert.setter
    def clientcert(self, val):  # pragma: no cover
        warnings.warn("Client.clientcert is deprecated, use Client.certificate_list instead.", DeprecationWarning)
        if val:
            self.certificate_list = [val]
        else:
            self.certificate_list = []


class Server(Connection):
    state: ConnectionState = ConnectionState.CLOSED
    peername: Optional[Address] = None
    sockname: Optional[Address] = None
    address: Optional[Address]

    timestamp_start: Optional[float] = None
    """TCP SYN sent"""
    timestamp_tcp_setup: Optional[float] = None
    """TCP ACK received"""

    sni: Union[bytes, Literal[True], None] = True
    """True: client SNI, False: no SNI, bytes: custom value"""
    via: Optional[server_spec.ServerSpec] = None

    def __init__(self, address: Optional[Address]):
        self.id = str(uuid.uuid4())
        self.address = address

    def get_state(self):
        return {
            'address': self.address,
            'alpn_proto_negotiated': self.alpn,
            'id': self.id,
            'ip_address': self.peername,
            'sni': self.sni,
            'source_address': self.sockname,
            'timestamp_end': self.timestamp_end,
            'timestamp_start': self.timestamp_start,
            'timestamp_tcp_setup': self.timestamp_tcp_setup,
            'timestamp_tls_setup': self.timestamp_tls_setup,
            'tls_established': self.tls_established,
            'tls_version': self.tls_version,
            'via': None,
            # only used in sans-io
            'state': self.state.value,
            'error': self.error,
            'tls': self.tls,
            'certificate_list': [x.get_state() for x in self.certificate_list],
            'alpn_offers': self.alpn_offers,
            'cipher_name': self.cipher,
            'cipher_list': self.cipher_list,
            'via2': self.via,
        }

    @classmethod
    def from_state(cls, state) -> "Server":
        server = Server(None)
        server.set_state(state)
        return server

    def set_state(self, state):
        self.address = tuple(state["address"]) if state["address"] else None
        self.alpn = state["alpn_proto_negotiated"]
        self.id = state["id"]
        self.peername = tuple(state["ip_address"]) if state["ip_address"] else None
        self.sni = state["sni"]
        self.sockname = tuple(state["source_address"]) if state["source_address"] else None
        self.timestamp_end = state["timestamp_end"]
        self.timestamp_start = state["timestamp_start"]
        self.timestamp_tcp_setup = state["timestamp_tcp_setup"]
        self.timestamp_tls_setup = state["timestamp_tls_setup"]
        self.tls_version = state["tls_version"]
        self.state = ConnectionState(state["state"])
        self.error = state["error"]
        self.tls = state["tls"]
        self.certificate_list = [certs.Cert.from_state(x) for x in state["certificate_list"]]
        self.alpn_offers = state["alpn_offers"]
        self.cipher = state["cipher_name"]
        self.cipher_list = state["cipher_list"]
        self.via = state["via2"]

    @property
    def ip_address(self) -> Optional[Address]:  # pragma: no cover
        warnings.warn("Server.ip_address is deprecated, use Server.peername instead.", DeprecationWarning, stacklevel=2)
        return self.peername

    @property
    def cert(self) -> Optional[certs.Cert]:  # pragma: no cover
        warnings.warn("Server.cert is deprecated, use Server.certificate_list instead.", DeprecationWarning, stacklevel=2)
        if self.certificate_list:
            return self.certificate_list[0]
        else:
            return None

    @cert.setter
    def cert(self, val):  # pragma: no cover
        warnings.warn("Server.cert is deprecated, use Server.certificate_list instead.", DeprecationWarning, stacklevel=2)
        if val:
            self.certificate_list = [val]
        else:
            self.certificate_list = []


class Context:
    """
    Layers get a context object that has all contextual information they require.
    """

    client: Client
    server: Server
    options: Options
    layers: List["mitmproxy.proxy.layer.Layer"]

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
