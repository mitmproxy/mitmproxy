from dataclasses import dataclass
from ssl import VerifyMode
from typing import List, Optional, Union

from aioquic.tls import CipherSuite
from cryptography import x509
from cryptography.hazmat.primitives.asymmetric import dsa, ec, rsa
from mitmproxy.proxy import layer
from mitmproxy.proxy.commands import StartHook
from mitmproxy.tls import TlsData


@dataclass
class QuicTlsSettings:
    """
    Settings necessary to establish QUIC's TLS context.
    """

    certificate: Optional[x509.Certificate] = None
    """The certificate to use for the connection."""
    certificate_chain: List[x509.Certificate] = []
    """An optional list of additional certificates to send to the peer."""
    certificate_private_key: Optional[
        Union[dsa.DSAPrivateKey, ec.EllipticCurvePrivateKey, rsa.RSAPrivateKey]
    ] = None
    """The certificate's private key."""
    cipher_suites: Optional[List[CipherSuite]] = None
    """An optional list of allowed/advertised protocols."""
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

    An addon is expected to initialize at least data.certificate and data.certificate_private_key.
    (by default, this is done by `mitmproxy.addons.tlsconfig`)
    """

    data: QuicTlsData


@dataclass
class QuicTlsStartServerHook(StartHook):
    """
    TLS negotation between mitmproxy and a server over QUIC is about to start.

    An addon is expected to initialize at least data.certificate and data.certificate_private_key.
    (by default, this is done by `mitmproxy.addons.tlsconfig`)
    """

    data: QuicTlsData


class QuicLayer(layer.Layer):
    pass


class QuicServerLayer(layer.Layer):
    pass


class QuicClientLayer(layer.Layer):
    pass
