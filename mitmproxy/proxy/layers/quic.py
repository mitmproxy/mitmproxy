import asyncio
from dataclasses import dataclass
from ssl import VerifyMode
from typing import Callable, List, Optional, TextIO, Union

from aioquic.buffer import Buffer as QuicBuffer
from aioquic.quic.configuration import QuicConfiguration
from aioquic.quic.connection import QuicConnection, QuicConnectionError
from aioquic.tls import (
    CipherSuite,
    Context as QuicTlsContext,
    HandshakeType,
    ServerHello,
    pull_server_hello,
)
from aioquic.quic.packet import PACKET_TYPE_INITIAL, pull_quic_header
from cryptography import x509
from cryptography.hazmat.primitives.asymmetric import dsa, ec, rsa
from mitmproxy import connection
from mitmproxy.net import tls
from mitmproxy.proxy import commands, context, events, layer, layers
from mitmproxy.proxy.utils import expect
from mitmproxy.tls import ClientHello, ClientHelloData, TlsData


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
class QuicTlsStartClientHook(connection.StartHook):
    """
    TLS negotiation between mitmproxy and a client over QUIC is about to start.

    An addon is expected to initialize data.settings.
    (by default, this is done by `mitmproxy.addons.tlsconfig`)
    """

    data: QuicTlsData


@dataclass
class QuicTlsStartServerHook(connection.StartHook):
    """
    TLS negotiation between mitmproxy and a server over QUIC is about to start.

    An addon is expected to initialize data.settings.
    (by default, this is done by `mitmproxy.addons.tlsconfig`)
    """

    data: QuicTlsData


class QuicSecretsLogger(TextIO):
    conn: connection.Connection
    logger: tls.MasterSecretLogger

    def __init__(
        self, conn: connection.Connection, logger: tls.MasterSecretLogger
    ) -> None:
        super().__init__()
        self.conn = conn
        self.logger = logger

    def write(self, s: str) -> int:
        self.logger(self.conn, s.encode())

    def flush(self) -> None:
        # done by the logger during write
        pass


@dataclass
class QuicClientHelloException(Exception):
    data: bytes


def hook_quic_tls(quic: QuicConnection, cb: Callable[[QuicTlsContext]]) -> None:
    assert quic.tls is None

    # patch aioquic to intercept the client/server hello
    orig_initialize = quic._initialize

    def initialize_replacement(peer_cid: bytes) -> None:
        try:
            return orig_initialize(peer_cid)
        finally:
            cb(quic.tls)

    quic._initialize = initialize_replacement


def raise_on_client_hello(tls: QuicTlsContext) -> None:
    def server_handle_hello_replacement(
        input_buf: QuicBuffer,
        initial_buf: QuicBuffer,
        handshake_buf: QuicBuffer,
        onertt_buf: QuicBuffer,
    ) -> None:
        assert input_buf.pull_uint8() == HandshakeType.CLIENT_HELLO
        length = 0
        for b in input_buf.pull_bytes(3):
            length = (length << 8) | b
        offset = input_buf.tell()
        raise QuicClientHelloException(
            data=input_buf.data_slice(offset, offset + length)
        )

    tls._server_handle_hello = server_handle_hello_replacement


def callback_on_server_hello(tls: QuicTlsContext, cb: Callable[[ServerHello]]) -> None:
    orig_client_handle_hello = tls._client_handle_hello

    def _client_handle_hello_replacement(
        input_buf: QuicBuffer,
        output_buf: QuicBuffer,
    ) -> None:
        offset = input_buf.tell()
        cb(pull_server_hello(input_buf))
        input_buf.seek(offset)
        orig_client_handle_hello(input_buf, output_buf)

    tls._client_handle_hello = _client_handle_hello_replacement


def read_client_hello(data: bytes, connection_id_length: int) -> ClientHello:
    buffer = QuicBuffer(data=data)
    header = pull_quic_header(
        buffer, host_cid_length=connection_id_length
    )
    assert header.packet_type == PACKET_TYPE_INITIAL
    temp_quic = QuicConnection(
        configuration=QuicConfiguration(connection_id_length=connection_id_length),
        original_destination_connection_id=header.destination_cid,
    )
    hook_quic_tls(temp_quic, raise_on_client_hello)
    try:
        temp_quic.receive_datagram(data, ("0.0.0.0", 0), now=0)
    except QuicClientHelloException as hello:
        try:
            return ClientHello(hello.data)
        except EOFError as e:
            raise ValueError("Invalid ClientHello data.") from e
    except QuicConnectionError as e:
        raise ValueError(e.reason_phrase) from e
    raise ValueError("No ClientHello returned.")


class QuicLayer(layer.Layer):
    loop: asyncio.AbstractEventLoop
    buffer: List[bytes]
    quic: Optional[QuicConnection]
    conn: connection.Connection
    issue_cid: Callable[[bytes]]
    retire_cid: Callable[[bytes]]

    def __init__(
        self,
        context: context.Context,
        conn: connection.Connection,
        issue_cid: Callable[[bytes]],
        retire_cid: Callable[[bytes]],
    ) -> None:
        super().__init__(context)
        self.loop = asyncio.get_event_loop()
        self.buffer = []
        self.quic = None
        self.conn = conn
        self.issue_cid = issue_cid
        self.retire_cid = retire_cid

    def build_configuration(self, settings: QuicTlsSettings) -> QuicConfiguration:
        return QuicConfiguration(
            alpn_protocols=self.conn.alpn_offers,
            connection_id_length=self.context.options.quic_connection_id_length,
            is_client=self.conn == self.context.server,
            secrets_log_file=QuicSecretsLogger(self.conn, tls.log_master_secret)
            if tls.log_master_secret is not None
            else None,
            server_name=self.conn.sni,
            cafile=settings.ca_file,
            capath=settings.ca_path,
            certificate=settings.certificate,
            certificate_chain=settings.certificate_chain,
            cipher_suites=settings.cipher_suites,
            private_key=settings.certificate_private_key,
            verify_mode=settings.verify_mode,
        )

    def initialize_connection(
        self, original_destination_connection_id: Union[bytes, None]
    ) -> layer.CommandGenerator[None]:
        assert not self.quic

        # (almost) identical to _TLSLayer.start_tls
        tls_data = QuicTlsData(self.conn, self.context)
        if self.conn == self.context.client:
            yield QuicTlsStartClientHook(tls_data)
        else:
            yield QuicTlsStartServerHook(tls_data)
        if not tls_data.settings:
            yield commands.Log(
                "No TLS settings were provided, failing connection.", "error"
            )
            yield commands.CloseConnection(self.conn)
            return
        assert tls_data.settings

        self.quic = QuicConnection(
            configuration=self.build_configuration(tls_data.settings),
            original_destination_connection_id=original_destination_connection_id,
        )
        self.issue_cid(self.quic.host_cid)


class ServerQuicLayer(QuicLayer):
    """
    This layer establishes QUIC for a single server connection.
    """

    def __init__(
        self,
        context: context.Context,
        issue_cid: Callable[[bytes]],
        retire_cid: Callable[[bytes]],
    ) -> None:
        super().__init__(context, context.server, issue_cid, retire_cid)


class ClientQuicLayer(QuicLayer):
    """
    This layer establishes QUIC on a single client connection.
    """

    def __init__(
        self,
        context: context.Context,
        issue_cid: Callable[[bytes]],
        retire_cid: Callable[[bytes]],
    ) -> None:
        super().__init__(context, context.client, issue_cid, retire_cid)

    @expect(events.Start)
    def handle_start(self, _: events.Event) -> layer.CommandGenerator[None]:
        self._handle_event = self.handle_client_hello
        yield from ()

    @expect(events.DataReceived, events.ConnectionClosed)
    def handle_client_hello(self, event: events.Event) -> layer.CommandGenerator[None]:
        if isinstance(event, events.DataReceived):
            assert event.connection == self.conn

            # extract the client hello
            try:
                client_hello = read_client_hello(event.data, connection_id_length=self.context.options.quic_connection_id_length)
            except ValueError as e:
                yield commands.Log(
                    f"Cannot parse ClientHello: {str(e)} ({event.data.hex()})", "warn"
                )
                yield commands.CloseConnection(self.conn)
            else:
                self.conn.sni = client_hello.sni
                self.conn.alpn_offers = client_hello.alpn_protocols

                # check with addons what we shall do
                hook_data = ClientHelloData(self.context, client_hello)
                yield layers.tls.TlsClienthelloHook(hook_data)
                if hook_data.ignore_connection:
                    # simply relay everything (including the client hello)
                    relay_layer = layers.TCPLayer(self.context, ignore=True)
                    self._handle_event = relay_layer.handle_event
                    yield from relay_layer.handle_event(events.Start())
                    yield from relay_layer.handle_event(event)

                elif hook_data.establish_server_tls_first:
                    pass

                else:
                    pass

        elif isinstance(event, events.ConnectionClosed):
            assert event.connection == self.conn
            self._handle_event = self.handle_done

        else:
            raise AssertionError(f"Unexpected event: {event}")

    @expect(events.DataReceived, events.ConnectionClosed)
    def handle_done(self, _) -> layer.CommandGenerator[None]:
        yield from ()

    _handle_event = handle_start
