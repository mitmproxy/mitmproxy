from abc import abstractmethod
import asyncio
from dataclasses import dataclass
from ssl import VerifyMode
from typing import Callable, List, Literal, Optional, Tuple, Union
from urllib.parse import non_hierarchical

from aioquic.buffer import Buffer as QuicBuffer
from aioquic.quic import events as quic_events
from aioquic.quic.configuration import QuicConfiguration
from aioquic.quic.connection import QuicConnection, QuicConnectionError
from aioquic.tls import CipherSuite, HandshakeType
from aioquic.quic.packet import PACKET_TYPE_INITIAL, pull_quic_header
from cryptography import x509
from cryptography.hazmat.primitives.asymmetric import dsa, ec, rsa
from mitmproxy import connection
from mitmproxy.net import tls
from mitmproxy.proxy import commands, context, events, layer, layers
from mitmproxy.tls import ClientHello, ClientHelloData, TlsData
from mitmproxy.utils import human


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
class QuicTlsStartClientHook(commands.StartHook):
    """
    TLS negotiation between mitmproxy and a client over QUIC is about to start.

    An addon is expected to initialize data.settings.
    (by default, this is done by `mitmproxy.addons.tlsconfig`)
    """

    data: QuicTlsData


@dataclass
class QuicTlsStartServerHook(commands.StartHook):
    """
    TLS negotiation between mitmproxy and a server over QUIC is about to start.

    An addon is expected to initialize data.settings.
    (by default, this is done by `mitmproxy.addons.tlsconfig`)
    """

    data: QuicTlsData


@dataclass
class QuicConnectionEvent(events.ConnectionEvent):
    event: quic_events.QuicEvent


@dataclass
class QuicGetConnection(commands.ConnectionCommand):  # -> QuicConnection
    blocking = True


@dataclass(repr=False)
class OpenGetConnectionCompleted(events.CommandCompleted):
    command: QuicGetConnection
    connection: QuicConnection


class QuicSecretsLogger:
    logger: tls.MasterSecretLogger

    def __init__(self, logger: tls.MasterSecretLogger) -> None:
        super().__init__()
        self.logger = logger

    def write(self, s: str) -> int:
        if s[-1:] == "\n":
            s = s[:-1]
        data = s.encode()
        self.logger(None, data)  # type: ignore
        return len(data) + 1

    def flush(self) -> None:
        # done by the logger during write
        pass


@dataclass
class QuicClientHello(Exception):
    data: bytes


def pull_client_hello_and_connection_id(data: bytes) -> Tuple[ClientHello, bytes]:
    # ensure the first packet is indeed the initial one
    buffer = QuicBuffer(data=data)
    header = pull_quic_header(buffer)
    if header.packet_type != PACKET_TYPE_INITIAL:
        raise ValueError("Packet is not initial one.")

    # patch aioquic to intercept the client hello
    quic = QuicConnection(
        configuration=QuicConfiguration(),
        original_destination_connection_id=header.destination_cid,
    )
    _initialize = quic._initialize

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
        raise QuicClientHello(data=input_buf.data_slice(offset, offset + length))

    def initialize_replacement(peer_cid: bytes) -> None:
        try:
            return _initialize(peer_cid)
        finally:
            quic.tls._server_handle_hello = server_handle_hello_replacement

    quic._initialize = initialize_replacement
    try:
        quic.receive_datagram(data, ("0.0.0.0", 0), now=0)
    except QuicClientHello as hello:
        try:
            return (ClientHello(hello.data), header.destination_cid)
        except EOFError as e:
            raise ValueError("Invalid ClientHello data.") from e
    except QuicConnectionError as e:
        raise ValueError(e.reason_phrase) from e
    raise ValueError("No ClientHello returned.")


class QuicLayer(layer.Layer):
    child_layer: Optional[layer.Layer]
    conn: connection.Connection
    loop: asyncio.AbstractEventLoop
    original_destination_connection_id: Optional[bytes]
    quic: Optional[QuicConnection]
    waiting_get_connection_commands: List[QuicGetConnection]

    def __init__(
        self,
        context: context.Context,
        conn: connection.Connection,
        issue_cid: Optional[Callable[[bytes], None]] = None,
        retire_cid: Optional[Callable[[bytes], None]] = None,
    ) -> None:
        super().__init__(context)
        self.child_layer = None
        self.conn = conn
        self.loop = asyncio.get_event_loop()
        self.original_destination_connection_id = None
        self.quic = None
        self.waiting_get_connection_commands = []
        self._issue_cid = issue_cid
        self._retire_cid = retire_cid

    def build_configuration(self, settings: QuicTlsSettings) -> QuicConfiguration:
        return QuicConfiguration(
            alpn_protocols=self.conn.alpn_offers,
            connection_id_length=self.context.options.quic_connection_id_length,
            is_client=self.conn is self.context.server,
            secrets_log_file=QuicSecretsLogger(tls.log_master_secret)  # type: ignore
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

    def event_to_child(self, event: events.Event) -> layer.CommandGenerator[None]:
        assert self.child_layer is not None

        # answer the child layers request for the connection
        for command in self.child_layer.handle_event(event):
            if (
                isinstance(command, QuicGetConnection)
                and command.connection is self.conn
            ):
                if self.quic is None:
                    self.waiting_get_connection_commands.append(command)
                else:
                    yield from self.child_layer.handle_event(
                        OpenGetConnectionCompleted(
                            command=command,
                            connection=self.quic,
                        )
                    )
            else:
                yield command

    def fail_connection(
        self,
        reason: str,
        level: Literal["error", "warn", "info", "alert", "debug"] = "warn",
    ) -> layer.CommandGenerator[None]:
        yield commands.Log(
            message=f"Failing connection {self.conn}: {reason}", level=level
        )
        if self.conn.connected:
            yield commands.CloseConnection(self.conn)
        self._handle_event = self.state_done

    def initialize_connection(self) -> layer.CommandGenerator[None]:
        assert self.quic is None
        self._handle_event = self.state_ready

        # (almost) identical to _TLSLayer.start_tls
        tls_data = QuicTlsData(self.conn, self.context)
        if self.conn is self.context.client:
            yield QuicTlsStartClientHook(tls_data)
        else:
            yield QuicTlsStartServerHook(tls_data)
        if not tls_data.settings:
            yield from self.fail_connection(
                "No TLS settings were provided, failing connection.", level="error"
            )
            return
        assert tls_data.settings is not None

        # create the connection and let the waiters know about it
        self.quic = QuicConnection(
            configuration=self.build_configuration(tls_data.settings),
            original_destination_connection_id=self.original_destination_connection_id,
        )
        if self._issue_cid:
            self._issue_cid(self.quic.host_cid)
        while self.waiting_get_connection_commands:
            assert self.quic is not None
            assert self.child_layer is not None
            yield from self.child_layer.handle_event(
                OpenGetConnectionCompleted(
                    command=self.waiting_get_connection_commands.pop(),
                    connection=self.quic,
                )
            )

    def process_events(self) -> layer.CommandGenerator[None]:
        assert self.quic is not None
        yield from ()

    @abstractmethod
    def start(self) -> layer.CommandGenerator[None]:
        yield from ()  # pragma: no cover

    def state_start(self, event: events.Event) -> layer.CommandGenerator[None]:
        assert isinstance(event, events.Start)

        # start this layer and the child layer
        yield from self.start()
        if self.child_layer is not None:
            yield from self.child_layer.handle_event(event)

    def state_ready(self, event: events.Event) -> layer.CommandGenerator[None]:
        assert self.quic is not None
        yield from ()

    def state_done(self, event: events.Event) -> layer.CommandGenerator[None]:
        yield from ()

    _handle_event = state_start


class ServerQuicLayer(QuicLayer):
    """
    This layer establishes QUIC for a single server connection.
    """

    def __init__(self, context: context.Context) -> None:
        super().__init__(context, context.server)

    def start(self) -> layer.CommandGenerator[None]:
        # ensure there is an UDP connection
        if not self.conn.connected:
            err = yield commands.OpenConnection(self.conn)
            if err is not None:
                self.fail_connection(
                    f"Failed to establish connection to {human.format_address(self.conn)}: {err}"
                )
                return

        # try to connect
        yield from self.initialize_connection()
        if self.quic is not None:
            self.quic.connect(addr=self.conn.peername, now=self.loop.time())
            yield from self.process_events()


class ClientQuicLayer(QuicLayer):
    """
    This layer establishes QUIC on a single client connection.
    """

    server_layer: Optional[ServerQuicLayer]
    buffered_packets: Optional[List[Tuple[bytes, connection.Address, float]]]

    def __init__(
        self,
        context: context.Context,
        issue_cid: Callable[[bytes], None],
        retire_cid: Callable[[bytes], None],
    ) -> None:
        super().__init__(context, context.client, issue_cid, retire_cid)
        self.server_layer = None
        self.buffered_packets = None

    def start_client_connection(self) -> layer.CommandGenerator[None]:
        assert self.buffered_packets is not None

        yield from self.initialize_connection()
        if self.quic is not None:
            for data, addr, now in self.buffered_packets:
                self.quic.receive_datagram(
                    data=data,
                    addr=addr,
                    now=now,
                )
            yield from self.process_events()

    def start(self) -> layer.CommandGenerator[None]:
        self._handle_event = self.state_wait_for_client_hello
        yield from ()

    def state_wait_for_client_hello(
        self, event: events.Event
    ) -> layer.CommandGenerator[None]:
        assert isinstance(event, events.ConnectionEvent)
        assert event.connection is self.conn

        if isinstance(event, events.DataReceived):
            assert event.remote_addr is not None

            # extract the client hello
            try:
                (
                    client_hello,
                    self.original_destination_connection_id,
                ) = pull_client_hello_and_connection_id(event.data)
            except ValueError as e:
                yield from self.fail_connection(
                    f"Cannot parse ClientHello: {str(e)} ({event.data.hex()})"
                )
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

                else:
                    # buffer the client hello
                    self.buffered_packets = [
                        (event.data, event.remote_addr, self.loop.time())
                    ]

                    # contact the upstream server first if so desired
                    if hook_data.establish_server_tls_first:
                        self.server_layer = ServerQuicLayer(self.context)
                        self._handle_event = self.state_wait_for_upstream_server
                        yield from self.state_wait_for_upstream_server(events.Start())
                    else:
                        yield from self.start_client_connection()

        elif isinstance(event, events.ConnectionClosed):
            # this is odd since this layer should only be created if there is a packet
            self._handle_event = self.state_done

        else:
            raise AssertionError(f"Unexpected event: {event}")

    def state_wait_for_upstream_server(
        self, event: events.Event
    ) -> layer.CommandGenerator[None]:
        assert self.buffered_packets is not None
        assert self.server_layer is not None

        # filter DataReceived and ConnectionClosed relating to the client connection
        if isinstance(event, events.ConnectionEvent):
            if event.connection is self.conn:
                if isinstance(event, events.DataReceived):
                    assert event.remote_addr is not None

                    # still waiting for the server, buffer the data
                    self.buffered_packets.append(
                        (event.data, event.remote_addr, self.loop.time())
                    )

                elif isinstance(event, events.ConnectionClosed):
                    # close the upstream connection as well and be done
                    self._handle_event = self.state_done
                    yield from self.server_layer.fail_connection(
                        "Client closed the connection."
                    )

                else:
                    raise AssertionError(f"Unexpected event: {event}")

        # forward the event and check it's results
        yield from self.server_layer.handle_event(event)
        if not self.context.server.connected:
            yield commands.Log(
                f"Unable to establish QUIC connection with server ({self.context.server.error or 'Connection closed.'}). "
                f"Trying to establish QUIC with client anyway."
            )
            yield from self.start_client_connection()
        elif self.context.server.tls_established:
            yield from self.start_client_connection()
