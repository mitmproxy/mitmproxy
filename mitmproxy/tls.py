import io
from dataclasses import dataclass
from typing import List, Optional, Tuple

from kaitaistruct import KaitaiStream

from OpenSSL import SSL
from mitmproxy import connection
from mitmproxy.contrib.kaitaistruct import tls_client_hello
from mitmproxy.net import check
from mitmproxy.proxy import context


class ClientHello:
    """
    A TLS ClientHello is the first message sent by the client when initiating TLS.
    """

    raw_bytes: bytes
    """The raw ClientHello bytes as seen on the wire"""

    def __init__(self, raw_client_hello: bytes):
        """Create a TLS ClientHello object from raw bytes."""
        self.raw_bytes = raw_client_hello
        self._client_hello = tls_client_hello.TlsClientHello(
            KaitaiStream(io.BytesIO(raw_client_hello))
        )

    @property
    def cipher_suites(self) -> List[int]:
        """The cipher suites offered by the client (as raw ints)."""
        return self._client_hello.cipher_suites.cipher_suites

    @property
    def sni(self) -> Optional[str]:
        """
        The [Server Name Indication](https://en.wikipedia.org/wiki/Server_Name_Indication),
        which indicates which hostname the client wants to connect to.
        """
        if self._client_hello.extensions:
            for extension in self._client_hello.extensions.extensions:
                is_valid_sni_extension = (
                    extension.type == 0x00 and
                    len(extension.body.server_names) == 1 and
                    extension.body.server_names[0].name_type == 0 and
                    check.is_valid_host(extension.body.server_names[0].host_name)
                )
                if is_valid_sni_extension:
                    return extension.body.server_names[0].host_name.decode("ascii")
        return None

    @property
    def alpn_protocols(self) -> List[bytes]:
        """
        The application layer protocols offered by the client as part of the
        [ALPN](https://en.wikipedia.org/wiki/Application-Layer_Protocol_Negotiation) TLS extension.
        """
        if self._client_hello.extensions:
            for extension in self._client_hello.extensions.extensions:
                if extension.type == 0x10:
                    return list(x.name for x in extension.body.alpn_protocols)
        return []

    @property
    def extensions(self) -> List[Tuple[int, bytes]]:
        """The raw list of extensions in the form of `(extension_type, raw_bytes)` tuples."""
        ret = []
        if self._client_hello.extensions:
            for extension in self._client_hello.extensions.extensions:
                body = getattr(extension, "_raw_body", extension.body)
                ret.append((extension.type, body))
        return ret

    def __repr__(self):
        return f"ClientHello(sni: {self.sni}, alpn_protocols: {self.alpn_protocols})"


@dataclass
class ClientHelloData:
    """
    Event data for `tls_clienthello` event hooks.
    """
    context: context.Context
    """The context object for this connection."""
    client_hello: ClientHello
    """The entire parsed TLS ClientHello."""
    ignore_connection: bool = False
    """
    If set to `True`, do not intercept this connection and forward encrypted contents unmodified.
    """
    establish_server_tls_first: bool = False
    """
    If set to `True`, pause this handshake and establish TLS with an upstream server first.
    This makes it possible to process the server certificate when generating an interception certificate.
    """


@dataclass
class TlsData:
    """
    Event data for `tls_start_client`, `tls_start_server`, and `tls_handshake` event hooks.
    """
    conn: connection.Connection
    """The affected connection."""
    context: context.Context
    """The context object for this connection."""
    ssl_conn: Optional[SSL.Connection] = None
    """
    The associated pyOpenSSL `SSL.Connection` object.
    This will be set by an addon in the `tls_start_*` event hooks.
    """
