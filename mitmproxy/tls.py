import io
from dataclasses import dataclass

from kaitaistruct import KaitaiStream
from OpenSSL import SSL

from mitmproxy import connection
from mitmproxy.contrib.kaitaistruct import dtls_client_hello
from mitmproxy.contrib.kaitaistruct import tls_client_hello
from mitmproxy.net import check
from mitmproxy.proxy import context


class ClientHello:
    """
    A TLS ClientHello is the first message sent by the client when initiating TLS.
    """

    _raw_bytes: bytes

    def __init__(self, raw_client_hello: bytes, dtls: bool = False):
        """Create a TLS ClientHello object from raw bytes."""
        self._raw_bytes = raw_client_hello
        if dtls:
            self._client_hello = dtls_client_hello.DtlsClientHello(
                KaitaiStream(io.BytesIO(raw_client_hello))
            )
        else:
            self._client_hello = tls_client_hello.TlsClientHello(
                KaitaiStream(io.BytesIO(raw_client_hello))
            )

    def raw_bytes(self, wrap_in_record: bool = True) -> bytes:
        """
        The raw ClientHello bytes as seen on the wire.

        If `wrap_in_record` is True, the ClientHello will be wrapped in a synthetic TLS record
        (`0x160303 + len(chm) + 0x01 + len(ch)`), which is the format expected by some tools.
        The synthetic record assumes TLS version (`0x0303`), which may be different from what has been sent over the
        wire. JA3 hashes are unaffected by this as they only use the TLS version from the ClientHello data structure.

        A future implementation may return not just the exact ClientHello, but also the exact record(s) as seen on the
        wire.
        """
        if isinstance(self._client_hello, dtls_client_hello.DtlsClientHello):
            raise NotImplementedError

        if wrap_in_record:
            return (
                # record layer
                b"\x16\x03\x03"
                + (len(self._raw_bytes) + 4).to_bytes(2, byteorder="big")
                +
                # handshake header
                b"\x01"
                + len(self._raw_bytes).to_bytes(3, byteorder="big")
                +
                # ClientHello as defined in https://datatracker.ietf.org/doc/html/rfc8446#section-4.1.2.
                self._raw_bytes
            )
        else:
            return self._raw_bytes

    @property
    def cipher_suites(self) -> list[int]:
        """The cipher suites offered by the client (as raw ints)."""
        return self._client_hello.cipher_suites.cipher_suites

    @property
    def sni(self) -> str | None:
        """
        The [Server Name Indication](https://en.wikipedia.org/wiki/Server_Name_Indication),
        which indicates which hostname the client wants to connect to.
        """
        if ext := getattr(self._client_hello, "extensions", None):
            for extension in ext.extensions:
                is_valid_sni_extension = (
                    extension.type == 0x00
                    and len(extension.body.server_names) == 1
                    and extension.body.server_names[0].name_type == 0
                    and check.is_valid_host(extension.body.server_names[0].host_name)
                )
                if is_valid_sni_extension:
                    return extension.body.server_names[0].host_name.decode("ascii")
        return None

    @property
    def alpn_protocols(self) -> list[bytes]:
        """
        The application layer protocols offered by the client as part of the
        [ALPN](https://en.wikipedia.org/wiki/Application-Layer_Protocol_Negotiation) TLS extension.
        """
        if ext := getattr(self._client_hello, "extensions", None):
            for extension in ext.extensions:
                if extension.type == 0x10:
                    return list(x.name for x in extension.body.alpn_protocols)
        return []

    @property
    def extensions(self) -> list[tuple[int, bytes]]:
        """The raw list of extensions in the form of `(extension_type, raw_bytes)` tuples."""
        ret = []
        if ext := getattr(self._client_hello, "extensions", None):
            for extension in ext.extensions:
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
    ssl_conn: SSL.Connection | None = None
    """
    The associated pyOpenSSL `SSL.Connection` object.
    This will be set by an addon in the `tls_start_*` event hooks.
    """
    is_dtls: bool = False
    """
    If set to `True`, indicates that it is a DTLS event.
    """
