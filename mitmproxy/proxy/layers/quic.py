from abc import abstractmethod
from dataclasses import dataclass
import io
from ssl import VerifyMode
from typing import List, Optional, Union

from aioquic.buffer import Buffer as QuicBuffer
from aioquic.quic.connection import QuicConnection
from aioquic.tls import CipherSuite, HandshakeType
from cryptography import x509
from cryptography.hazmat.primitives.asymmetric import dsa, ec, rsa
from mitmproxy.proxy import layer
from mitmproxy.proxy.commands import StartHook
from mitmproxy.proxy.context import Context
from mitmproxy.tls import TlsData


@dataclass
class QuicTlsSettings:
    """
    Settings necessary to establish QUIC's TLS context.
    """

    certificate: Optional[x509.Certificate] = None
    """The certificate to use for the connection."""
    certificate_chain: List[x509.Certificate] = []
    """A list of additional certificates to send to the peer."""
    certificate_private_key: Optional[
        Union[dsa.DSAPrivateKey, ec.EllipticCurvePrivateKey, rsa.RSAPrivateKey]
    ] = None
    """The certificate's private key."""
    cipher_suites: Optional[List[CipherSuite]] = None
    """An optional list of allowed/advertised cipher suites."""
    ca_path: Optional[str] = None
    """An optional path to a directory that contains the necessary information to verify the peer certificate."""
    ca_file: Optional[str] = None
    """An optional path to a PEM file that will be used to verify the peer certificate."""
    verify_mode: Optional[VerifyMode] = None
    """An optional flag that specifies how/if the peer's certificate should be validated."""


@dataclass
class QuicTlsData(TlsData):
    """
    Event data for `quic_tls_start_client` and `quic_tls_start_server` event hooks.
    """

    settings: Optional[QuicTlsSettings] = None
    """
    The associated `QuicTlsSettings` object.
    This will be set by an addon in the `quic_tls_start_*` event hooks.
    """


@dataclass
class QuicTlsStartClientHook(StartHook):
    """
    TLS negotation between mitmproxy and a client over QUIC is about to start.

    An addon is expected to initialize data.settings.
    (by default, this is done by `mitmproxy.addons.tlsconfig`)
    """

    data: QuicTlsData


@dataclass
class QuicTlsStartServerHook(StartHook):
    """
    TLS negotation between mitmproxy and a server over QUIC is about to start.

    An addon is expected to initialize data.settings.
    (by default, this is done by `mitmproxy.addons.tlsconfig`)
    """

    data: QuicTlsData


class QuicLayer(layer.Layer):
    conn: QuicConnection


self._protocols[connection.host_cid] = protocol

    def _connection_id_issued(self, cid: bytes, protocol: QuicConnectionProtocol):
        self._protocols[cid] = protocol

    def _connection_id_retired(
        self, cid: bytes, protocol: QuicConnectionProtocol
    ) -> None:
        assert self._protocols[cid] == protocol
        del self._protocols[cid]

    def _connection_terminated(self, protocol: QuicConnectionProtocol):
        for cid, proto in list(self._protocols.items()):
            if proto == protocol:
                del self._protocols[cid]


class ServerQuicLayer(QuicLayer):
    """
    This layer establishes QUIC for a single server connection.
    """
    pass


@dataclass
class ClientHelloException(Exception):
    data: bytes


class ClientQuicLayer(QuicLayer):
    _intercept_client_hello: bool

    """
    This layer establishes QUIC on a single client connection.
    """

    def __init__(self, context: Context) -> None:
        super().__init__(context)

        # patch aioquic to intercept the client hello
        orig_initialize = self.conn._initialize
        def initialize_replacement(peer_cid: bytes) -> None:
            try:
                return orig_initialize(peer_cid)
            finally:
                orig_server_handle_hello = self.conn.tls._server_handle_hello
                def server_handle_hello_replacement(
                    input_buf: QuicBuffer,
                    initial_buf: QuicBuffer,
                    handshake_buf: QuicBuffer,
                    onertt_buf: QuicBuffer,
                ) -> None:
                    if self._intercept_client_hello and input_buf.pull_uint8() == HandshakeType.CLIENT_HELLO:
                        raise ClientHelloException(input_buf.data[:input_buf.tell()])
                    else:
                        orig_server_handle_hello(input_buf, initial_buf, handshake_buf, onertt_buf)
                self.conn.tls._server_handle_hello = server_handle_hello_replacement
        self.conn._initialize = initialize_replacement
