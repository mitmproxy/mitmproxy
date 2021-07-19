import uuid
import warnings
from abc import ABCMeta
from enum import Flag
from typing import Optional, Sequence, Tuple

from mitmproxy import certs
from mitmproxy.coretypes import serializable
from mitmproxy.net import server_spec
from mitmproxy.utils import human


class ConnectionState(Flag):
    """The current state of the underlying socket."""
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
    Base class for client and server connections.

    The connection object only exposes metadata about the connection, but not the underlying socket object.
    This is intentional, all I/O should be handled by `mitmproxy.proxy.server` exclusively.
    """
    # all connections have a unique id. While
    # f.client_conn == f2.client_conn already holds true for live flows (where we have object identity),
    # we also want these semantics for recorded flows.
    id: str
    """A unique UUID to identify the connection."""
    state: ConnectionState
    """The current connection state."""
    peername: Optional[Address]
    """The remote's `(ip, port)` tuple for this connection."""
    sockname: Optional[Address]
    """Our local `(ip, port)` tuple for this connection."""
    error: Optional[str] = None
    """
    A string describing a general error with connections to this address.

    The purpose of this property is to signal that new connections to the particular endpoint should not be attempted,
    for example because it uses an untrusted TLS certificate. Regular (unexpected) disconnects do not set the error
    property. This property is only reused per client connection.
    """

    tls: bool = False
    """
    `True` if TLS should be established, `False` otherwise.
    Note that this property only describes if a connection should eventually be protected using TLS.
    To check if TLS has already been established, use `Connection.tls_established`.
    """
    certificate_list: Sequence[certs.Cert] = ()
    """
    The TLS certificate list as sent by the peer.
    The first certificate is the end-entity certificate.

    > [RFC 8446] Prior to TLS 1.3, "certificate_list" ordering required each
    > certificate to certify the one immediately preceding it; however,
    > some implementations allowed some flexibility.  Servers sometimes
    > send both a current and deprecated intermediate for transitional
    > purposes, and others are simply configured incorrectly, but these
    > cases can nonetheless be validated properly.  For maximum
    > compatibility, all implementations SHOULD be prepared to handle
    > potentially extraneous certificates and arbitrary orderings from any
    > TLS version, with the exception of the end-entity certificate which
    > MUST be first.
    """
    alpn: Optional[bytes] = None
    """The application-layer protocol as negotiated using
    [ALPN](https://en.wikipedia.org/wiki/Application-Layer_Protocol_Negotiation)."""
    alpn_offers: Sequence[bytes] = ()
    """The ALPN offers as sent in the ClientHello."""
    # we may want to add SSL_CIPHER_description here, but that's currently not exposed by cryptography
    cipher: Optional[str] = None
    """The active cipher name as returned by OpenSSL's `SSL_CIPHER_get_name`."""
    cipher_list: Sequence[str] = ()
    """Ciphers accepted by the proxy server on this connection."""
    tls_version: Optional[str] = None
    """The active TLS version."""
    sni: Optional[str] = None
    """
    The [Server Name Indication (SNI)](https://en.wikipedia.org/wiki/Server_Name_Indication) sent in the ClientHello.
    """

    timestamp_start: Optional[float]
    timestamp_end: Optional[float] = None
    """*Timestamp:* Connection has been closed."""
    timestamp_tls_setup: Optional[float] = None
    """*Timestamp:* TLS handshake has been completed successfully."""

    @property
    def connected(self) -> bool:
        """*Read-only:* `True` if Connection.state is ConnectionState.OPEN, `False` otherwise."""
        return self.state is ConnectionState.OPEN

    @property
    def tls_established(self) -> bool:
        """*Read-only:* `True` if TLS has been established, `False` otherwise."""
        return self.timestamp_tls_setup is not None

    def __eq__(self, other):
        if isinstance(other, Connection):
            return self.id == other.id
        return False

    def __hash__(self):
        return hash(self.id)

    def __repr__(self):
        attrs = repr({
            k: {
                "cipher_list": lambda: f"<{len(v)} ciphers>",
                "id": lambda: f"…{v[-6:]}"
            }.get(k, lambda: v)()
            for k, v in self.__dict__.items()
        })
        return f"{type(self).__name__}({attrs})"

    @property
    def alpn_proto_negotiated(self) -> Optional[bytes]:  # pragma: no cover
        """*Deprecated:* An outdated alias for Connection.alpn."""
        warnings.warn("Connection.alpn_proto_negotiated is deprecated, use Connection.alpn instead.",
                      DeprecationWarning)
        return self.alpn


class Client(Connection):
    """A connection between a client and mitmproxy."""
    peername: Address
    """The client's address."""
    sockname: Address
    """The local address we received this connection on."""

    mitmcert: Optional[certs.Cert] = None
    """
    The certificate used by mitmproxy to establish TLS with the client.
    """

    timestamp_start: float
    """*Timestamp:* TCP SYN received"""

    def __init__(self, peername: Address, sockname: Address, timestamp_start: float):
        self.id = str(uuid.uuid4())
        self.peername = peername
        self.sockname = sockname
        self.timestamp_start = timestamp_start
        self.state = ConnectionState.OPEN

    def __str__(self):
        if self.alpn:
            tls_state = f", alpn={self.alpn.decode(errors='replace')}"
        elif self.tls_established:
            tls_state = ", tls"
        else:
            tls_state = ""
        return f"Client({human.format_address(self.peername)}, state={self.state.name.lower()}{tls_state})"

    def get_state(self):
        # Important: Retain full compatibility with old proxy core for now!
        # This means we need to add all new fields to the old implementation.
        return {
            'address': self.peername,
            'alpn': self.alpn,
            'cipher_name': self.cipher,
            'id': self.id,
            'mitmcert': self.mitmcert.get_state() if self.mitmcert is not None else None,
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
        self.alpn = state["alpn"]
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
        self.mitmcert = certs.Cert.from_state(state["mitmcert"]) if state["mitmcert"] is not None else None
        self.alpn_offers = state["alpn_offers"]
        self.cipher_list = state["cipher_list"]

    @property
    def address(self):  # pragma: no cover
        """*Deprecated:* An outdated alias for Client.peername."""
        warnings.warn("Client.address is deprecated, use Client.peername instead.", DeprecationWarning, stacklevel=2)
        return self.peername

    @address.setter
    def address(self, x):  # pragma: no cover
        warnings.warn("Client.address is deprecated, use Client.peername instead.", DeprecationWarning, stacklevel=2)
        self.peername = x

    @property
    def cipher_name(self) -> Optional[str]:  # pragma: no cover
        """*Deprecated:* An outdated alias for Connection.cipher."""
        warnings.warn("Client.cipher_name is deprecated, use Client.cipher instead.", DeprecationWarning, stacklevel=2)
        return self.cipher

    @property
    def clientcert(self) -> Optional[certs.Cert]:  # pragma: no cover
        """*Deprecated:* An outdated alias for Connection.certificate_list[0]."""
        warnings.warn("Client.clientcert is deprecated, use Client.certificate_list instead.", DeprecationWarning,
                      stacklevel=2)
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
    """A connection between mitmproxy and an upstream server."""

    peername: Optional[Address] = None
    """The server's resolved `(ip, port)` tuple. Will be set during connection establishment."""
    sockname: Optional[Address] = None
    address: Optional[Address]
    """The server's `(host, port)` address tuple. The host can either be a domain or a plain IP address."""

    timestamp_start: Optional[float] = None
    """*Timestamp:* TCP SYN sent."""
    timestamp_tcp_setup: Optional[float] = None
    """*Timestamp:* TCP ACK received."""

    via: Optional[server_spec.ServerSpec] = None
    """An optional proxy server specification via which the connection should be established."""

    def __init__(self, address: Optional[Address]):
        self.id = str(uuid.uuid4())
        self.address = address
        self.state = ConnectionState.CLOSED

    def __str__(self):
        if self.alpn:
            tls_state = f", alpn={self.alpn.decode(errors='replace')}"
        elif self.tls_established:
            tls_state = ", tls"
        else:
            tls_state = ""
        if self.sockname:
            local_port = f", src_port={self.sockname[1]}"
        else:
            local_port = ""
        return f"Server({human.format_address(self.address)}, state={self.state.name.lower()}{tls_state}{local_port})"

    def __setattr__(self, name, value):
        if name == "address":
            connection_open = self.__dict__.get("state", ConnectionState.CLOSED) is ConnectionState.OPEN
            # assigning the current value is okay, that may be an artifact of calling .set_state().
            address_changed = self.__dict__.get("address") != value
            if connection_open and address_changed:
                raise RuntimeError("Cannot change server address on open connection.")
        return super().__setattr__(name, value)

    def get_state(self):
        return {
            'address': self.address,
            'alpn': self.alpn,
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
        self.alpn = state["alpn"]
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
        """*Deprecated:* An outdated alias for `Server.peername`."""
        warnings.warn("Server.ip_address is deprecated, use Server.peername instead.", DeprecationWarning, stacklevel=2)
        return self.peername

    @property
    def cert(self) -> Optional[certs.Cert]:  # pragma: no cover
        """*Deprecated:* An outdated alias for `Connection.certificate_list[0]`."""
        warnings.warn("Server.cert is deprecated, use Server.certificate_list instead.", DeprecationWarning,
                      stacklevel=2)
        if self.certificate_list:
            return self.certificate_list[0]
        else:
            return None

    @cert.setter
    def cert(self, val):  # pragma: no cover
        warnings.warn("Server.cert is deprecated, use Server.certificate_list instead.", DeprecationWarning,
                      stacklevel=2)
        if val:
            self.certificate_list = [val]
        else:
            self.certificate_list = []


__all__ = [
    "Connection",
    "Client",
    "Server",
    "ConnectionState"
]
