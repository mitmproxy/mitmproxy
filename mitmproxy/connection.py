import dataclasses
import time
import uuid
import warnings
from abc import ABCMeta
from collections.abc import Sequence
from dataclasses import dataclass
from dataclasses import field
from enum import Flag
from typing import Literal

from mitmproxy import certs
from mitmproxy.coretypes import serializable
from mitmproxy.net import server_spec
from mitmproxy.proxy import mode_specs
from mitmproxy.utils import human


class ConnectionState(Flag):
    """The current state of the underlying socket."""

    CLOSED = 0
    CAN_READ = 1
    CAN_WRITE = 2
    OPEN = CAN_READ | CAN_WRITE


TransportProtocol = Literal["tcp", "udp"]


# practically speaking we may have IPv6 addresses with flowinfo and scope_id,
# but type checking isn't good enough to properly handle tuple unions.
# this version at least provides useful type checking messages.
Address = tuple[str, int]

kw_only = {"kw_only": True}


# noinspection PyDataclass
@dataclass(**kw_only)
class Connection(serializable.SerializableDataclass, metaclass=ABCMeta):
    """
    Base class for client and server connections.

    The connection object only exposes metadata about the connection, but not the underlying socket object.
    This is intentional, all I/O should be handled by `mitmproxy.proxy.server` exclusively.
    """

    peername: Address | None
    """The remote's `(ip, port)` tuple for this connection."""
    sockname: Address | None
    """Our local `(ip, port)` tuple for this connection."""

    state: ConnectionState = field(
        default=ConnectionState.CLOSED, metadata={"serialize": False}
    )
    """The current connection state."""

    # all connections have a unique id. While
    # f.client_conn == f2.client_conn already holds true for live flows (where we have object identity),
    # we also want these semantics for recorded flows.
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    """A unique UUID to identify the connection."""
    transport_protocol: TransportProtocol = field(default="tcp")
    """The connection protocol in use."""
    error: str | None = None
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
    alpn: bytes | None = None
    """The application-layer protocol as negotiated using
    [ALPN](https://en.wikipedia.org/wiki/Application-Layer_Protocol_Negotiation)."""
    alpn_offers: Sequence[bytes] = ()
    """The ALPN offers as sent in the ClientHello."""
    # we may want to add SSL_CIPHER_description here, but that's currently not exposed by cryptography
    cipher: str | None = None
    """The active cipher name as returned by OpenSSL's `SSL_CIPHER_get_name`."""
    cipher_list: Sequence[str] = ()
    """Ciphers accepted by the proxy server on this connection."""
    tls_version: str | None = None
    """The active TLS version."""
    sni: str | None = None
    """
    The [Server Name Indication (SNI)](https://en.wikipedia.org/wiki/Server_Name_Indication) sent in the ClientHello.
    """

    timestamp_start: float | None = None
    timestamp_end: float | None = None
    """*Timestamp:* Connection has been closed."""
    timestamp_tls_setup: float | None = None
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
        attrs = {
            # ensure these come first.
            "id": None,
            "address": None,
        }
        for f in dataclasses.fields(self):
            val = getattr(self, f.name)
            if val != f.default:
                if f.name == "cipher_list":
                    val = f"<{len(val)} ciphers>"
                elif f.name == "id":
                    val = f"…{val[-6:]}"
                attrs[f.name] = val
        return f"{type(self).__name__}({attrs!r})"

    @property
    def alpn_proto_negotiated(self) -> bytes | None:  # pragma: no cover
        """*Deprecated:* An outdated alias for Connection.alpn."""
        warnings.warn(
            "Connection.alpn_proto_negotiated is deprecated, use Connection.alpn instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.alpn


# noinspection PyDataclass
@dataclass(eq=False, repr=False, **kw_only)
class Client(Connection):
    """A connection between a client and mitmproxy."""

    peername: Address
    """The client's address."""
    sockname: Address
    """The local address we received this connection on."""

    mitmcert: certs.Cert | None = None
    """
    The certificate used by mitmproxy to establish TLS with the client.
    """

    proxy_mode: mode_specs.ProxyMode = field(
        default=mode_specs.ProxyMode.parse("regular")
    )
    """The proxy server type this client has been connecting to."""

    timestamp_start: float = field(default_factory=time.time)
    """*Timestamp:* TCP SYN received"""

    def __str__(self):
        if self.alpn:
            tls_state = f", alpn={self.alpn.decode(errors='replace')}"
        elif self.tls_established:
            tls_state = ", tls"
        else:
            tls_state = ""
        state = self.state.name
        assert state
        return f"Client({human.format_address(self.peername)}, state={state.lower()}{tls_state})"

    @property
    def address(self):  # pragma: no cover
        """*Deprecated:* An outdated alias for Client.peername."""
        warnings.warn(
            "Client.address is deprecated, use Client.peername instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.peername

    @address.setter
    def address(self, x):  # pragma: no cover
        warnings.warn(
            "Client.address is deprecated, use Client.peername instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        self.peername = x

    @property
    def cipher_name(self) -> str | None:  # pragma: no cover
        """*Deprecated:* An outdated alias for Connection.cipher."""
        warnings.warn(
            "Client.cipher_name is deprecated, use Client.cipher instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.cipher

    @property
    def clientcert(self) -> certs.Cert | None:  # pragma: no cover
        """*Deprecated:* An outdated alias for Connection.certificate_list[0]."""
        warnings.warn(
            "Client.clientcert is deprecated, use Client.certificate_list instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        if self.certificate_list:
            return self.certificate_list[0]
        else:
            return None

    @clientcert.setter
    def clientcert(self, val):  # pragma: no cover
        warnings.warn(
            "Client.clientcert is deprecated, use Client.certificate_list instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        if val:
            self.certificate_list = [val]
        else:
            self.certificate_list = []


# noinspection PyDataclass
@dataclass(eq=False, repr=False, **kw_only)
class Server(Connection):
    """A connection between mitmproxy and an upstream server."""

    address: Address | None  # type: ignore
    """
    The server's `(host, port)` address tuple.

    The host can either be a domain or a plain IP address.
    Which of those two will be present depends on the proxy mode and the client.
    For explicit proxies, this value will reflect what the client instructs mitmproxy to connect to.
    For example, if the client starts off a connection with `CONNECT example.com HTTP/1.1`, it will be `example.com`.
    For transparent proxies such as WireGuard mode, this value will be an IP address.
    """

    peername: Address | None = None
    """
    The server's resolved `(ip, port)` tuple. Will be set during connection establishment.
    May be `None` in upstream proxy mode when the address is resolved by the upstream proxy only.
    """
    sockname: Address | None = None

    timestamp_start: float | None = None
    """
    *Timestamp:* Connection establishment started.

    For IP addresses, this corresponds to sending a TCP SYN; for domains, this corresponds to starting a DNS lookup.
    """
    timestamp_tcp_setup: float | None = None
    """*Timestamp:* TCP ACK received."""

    via: server_spec.ServerSpec | None = None
    """An optional proxy server specification via which the connection should be established."""

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
        state = self.state.name
        assert state
        return f"Server({human.format_address(self.address)}, state={state.lower()}{tls_state}{local_port})"

    def __setattr__(self, name, value):
        if name in ("address", "via"):
            connection_open = (
                self.__dict__.get("state", ConnectionState.CLOSED)
                is ConnectionState.OPEN
            )
            # assigning the current value is okay, that may be an artifact of calling .set_state().
            attr_changed = self.__dict__.get(name) != value
            if connection_open and attr_changed:
                raise RuntimeError(f"Cannot change server.{name} on open connection.")
        return super().__setattr__(name, value)

    @property
    def ip_address(self) -> Address | None:  # pragma: no cover
        """*Deprecated:* An outdated alias for `Server.peername`."""
        warnings.warn(
            "Server.ip_address is deprecated, use Server.peername instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.peername

    @property
    def cert(self) -> certs.Cert | None:  # pragma: no cover
        """*Deprecated:* An outdated alias for `Connection.certificate_list[0]`."""
        warnings.warn(
            "Server.cert is deprecated, use Server.certificate_list instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        if self.certificate_list:
            return self.certificate_list[0]
        else:
            return None

    @cert.setter
    def cert(self, val):  # pragma: no cover
        warnings.warn(
            "Server.cert is deprecated, use Server.certificate_list instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        if val:
            self.certificate_list = [val]
        else:
            self.certificate_list = []


__all__ = ["Connection", "Client", "Server", "ConnectionState"]
