from __future__ import annotations
import asyncio
from dataclasses import dataclass, field
from logging import DEBUG, ERROR, WARNING
from ssl import VerifyMode
import time
from typing import TYPE_CHECKING

from aioquic.buffer import Buffer as QuicBuffer
from aioquic.h3.connection import H3_ALPN, ErrorCode as H3ErrorCode
from aioquic.quic import events as quic_events
from aioquic.quic.configuration import QuicConfiguration
from aioquic.quic.connection import (
    QuicConnection,
    QuicConnectionError,
    QuicConnectionState,
    QuicErrorCode,
    stream_is_client_initiated,
    stream_is_unidirectional,
)
from aioquic.tls import CipherSuite, HandshakeType
from aioquic.quic.packet import (
    PACKET_TYPE_INITIAL,
    QuicProtocolVersion,
    encode_quic_version_negotiation,
    pull_quic_header,
)
from cryptography import x509
from cryptography.hazmat.primitives.asymmetric import dsa, ec, rsa
from mitmproxy import certs, connection
from mitmproxy.net import tls
from mitmproxy.proxy import commands, context, events, layer, tunnel
from mitmproxy.proxy.layers.tcp import TCPLayer
from mitmproxy.proxy.layers.tls import (
    TlsClienthelloHook,
    TlsEstablishedClientHook,
    TlsEstablishedServerHook,
    TlsFailedClientHook,
    TlsFailedServerHook,
)
from mitmproxy.proxy.layers.udp import UDPLayer
from mitmproxy.tls import ClientHello, ClientHelloData, TlsData

if TYPE_CHECKING:
    from mitmproxy.proxy.server import ConnectionHandler


@dataclass
class QuicTlsSettings:
    """
    Settings necessary to establish QUIC's TLS context.
    """

    certificate: x509.Certificate | None = None
    """The certificate to use for the connection."""
    certificate_chain: list[x509.Certificate] = field(default_factory=list)
    """A list of additional certificates to send to the peer."""
    certificate_private_key: dsa.DSAPrivateKey | ec.EllipticCurvePrivateKey | rsa.RSAPrivateKey | None = None
    """The certificate's private key."""
    cipher_suites: list[CipherSuite] | None = None
    """An optional list of allowed/advertised cipher suites."""
    ca_path: str | None = None
    """An optional path to a directory that contains the necessary information to verify the peer certificate."""
    ca_file: str | None = None
    """An optional path to a PEM file that will be used to verify the peer certificate."""
    verify_mode: VerifyMode | None = None
    """An optional flag that specifies how/if the peer's certificate should be validated."""


@dataclass
class QuicTlsData(TlsData):
    """
    Event data for `quic_start_client` and `quic_start_server` event hooks.
    """

    settings: QuicTlsSettings | None = None
    """
    The associated `QuicTlsSettings` object.
    This will be set by an addon in the `quic_start_*` event hooks.
    """


@dataclass
class QuicStartClientHook(commands.StartHook):
    """
    TLS negotiation between mitmproxy and a client over QUIC is about to start.

    An addon is expected to initialize data.settings.
    (by default, this is done by `mitmproxy.addons.tlsconfig`)
    """

    data: QuicTlsData


@dataclass
class QuicStartServerHook(commands.StartHook):
    """
    TLS negotiation between mitmproxy and a server over QUIC is about to start.

    An addon is expected to initialize data.settings.
    (by default, this is done by `mitmproxy.addons.tlsconfig`)
    """

    data: QuicTlsData


@dataclass
class QuicStreamEvent(events.ConnectionEvent):
    """Base class for all QUIC stream events."""

    stream_id: int
    """The ID of the stream the event was fired for."""


@dataclass
class QuicStreamDataReceived(QuicStreamEvent):
    """Event that is fired whenever data is received on a stream."""

    data: bytes
    """The data which was received."""
    end_stream: bool
    """Whether the STREAM frame had the FIN bit set."""


@dataclass
class QuicStreamReset(QuicStreamEvent):
    """Event that is fired when the remote peer resets a stream."""

    error_code: int
    """The error code that triggered the reset."""


class QuicStreamCommand(commands.ConnectionCommand):
    """Base class for all QUIC stream commands."""

    stream_id: int
    """The ID of the stream the command was issued for."""

    def __init__(self, connection: connection.Connection, stream_id: int):
        super().__init__(connection)
        self.stream_id = stream_id


class SendQuicStreamData(QuicStreamCommand):
    """Command that sends data on a stream."""

    data: bytes
    """The data which should be sent."""
    end_stream: bool
    """Whether the FIN bit should be set in the STREAM frame."""

    def __init__(self, connection: connection.Connection, stream_id: int, data: bytes, end_stream: bool = False):
        super().__init__(connection, stream_id)
        self.data = data
        self.end_stream = end_stream


class ResetQuicStream(QuicStreamCommand):
    """Abruptly terminate the sending part of a stream."""

    error_code: int
    """An error code indicating why the stream is being reset."""

    def __init__(self, connection: connection.Connection, stream_id: int, error_code: int):
        super().__init__(connection, stream_id)
        self.error_code = error_code


class StopQuicStream(QuicStreamCommand):
    """Request termination of the receiving part of a stream."""

    error_code: int
    """An error code indicating why the stream is being stopped."""

    def __init__(self, connection: connection.Connection, stream_id: int, error_code: int):
        super().__init__(connection, stream_id)
        self.error_code = error_code


class QuicSecretsLogger:
    logger: tls.MasterSecretLogger

    def __init__(self, logger: tls.MasterSecretLogger) -> None:
        super().__init__()
        self.logger = logger

    def write(self, s: str) -> int:
        if s[-1:] == "\n":
            s = s[:-1]
        data = s.encode("ascii")
        self.logger(None, data)  # type: ignore
        return len(data) + 1

    def flush(self) -> None:
        # done by the logger during write
        pass


def error_code_to_str(error_code: int) -> str:
    """Returns the corresponding name of the given error code or a string containing its numeric value."""

    try:
        return H3ErrorCode(error_code).name
    except ValueError:
        try:
            return QuicErrorCode(error_code).name
        except ValueError:
            return f"unknown error (0x{error_code:x})"


def get_connection_error(conn: connection.Connection) -> quic_events.ConnectionTerminated | None:
    """Returns the QUIC close event that is associated with the given connection."""

    close_event = getattr(conn, "quic_error", None)
    if close_event is None:
        return None
    assert isinstance(close_event, quic_events.ConnectionTerminated)
    return close_event


def is_success_error_code(error_code: int) -> bool:
    """Returns whether the given error code actually indicates no error."""

    return error_code in (QuicErrorCode.NO_ERROR, H3ErrorCode.H3_NO_ERROR)


def get_stream_connection_state(stream_id: int, is_client: bool) -> connection.ConnectionState:
    """Returns the initial connection state of a stream."""

    state = connection.ConnectionState.OPEN
    if stream_is_unidirectional(stream_id):
        if stream_is_client_initiated(stream_id) == is_client:
            state &= ~connection.ConnectionState.CAN_READ
        else:
            state &= ~connection.ConnectionState.CAN_WRITE
    return state


def set_connection_error(conn: connection.Connection, close_event: quic_events.ConnectionTerminated) -> None:
    """Stores the given close event for the given connection."""

    setattr(conn, "quic_error", close_event)


@dataclass
class QuicClientHello(Exception):
    """Helper error only used in `quic_parse_client_hello`."""

    data: bytes


def quic_parse_client_hello(data: bytes) -> ClientHello:
    """Helper function that parses a client hello packet."""

    # ensure the first packet is indeed the initial one
    buffer = QuicBuffer(data=data)
    header = pull_quic_header(buffer)
    if header.packet_type != PACKET_TYPE_INITIAL:
        raise ValueError("Packet is not initial one.")

    # patch aioquic to intercept the client hello
    quic = QuicConnection(
        configuration=QuicConfiguration(
            is_client=False,
            certificate="",
            private_key="",
        ),
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
        raise QuicClientHello(input_buf.data_slice(offset, offset + length))

    def initialize_replacement(peer_cid: bytes) -> None:
        try:
            return _initialize(peer_cid)
        finally:
            quic.tls._server_handle_hello = server_handle_hello_replacement  # type: ignore

    quic._initialize = initialize_replacement  # type: ignore
    try:
        quic.receive_datagram(data, ("0.0.0.0", 0), now=0)
    except QuicClientHello as hello:
        try:
            return ClientHello(hello.data)
        except EOFError as e:
            raise ValueError("Invalid ClientHello data.") from e
    except QuicConnectionError as e:
        raise ValueError(e.reason_phrase) from e
    raise ValueError("No ClientHello returned.")


class QuicStreamLayer(layer.Layer):
    """
    Layer for QUIC streams.
    Serves as a marker for NextLayer and keeps track of the connection states.
    """

    client: connection.Client
    client_stream_id: int
    server: connection.Server
    server_stream_id: int | None
    child_layer: layer.Layer

    def __init__(self, context: context.Context, ignore: bool, client_stream_id: int, server_stream_id: int | None) -> None:
        # We mustn't reuse client or server from the QUIC connection as we have different states here.
        # Also, we store the original values to detect if the context has changed.
        self.client = context.client = connection.Client(
            peername=context.client.peername,
            sockname=context.client.sockname,
            timestamp_start=time.time(),
            transport_protocol="tcp",
            proxy_mode=context.client.proxy_mode,
        )
        self.server = context.server = connection.Server(
            address=context.server.address,
            transport_protocol="tcp",
        )
        super().__init__(context)
        self.client_stream_id = client_stream_id
        self.server_stream_id = server_stream_id
        self.child_layer = (
            TCPLayer(context, ignore=True)
            if ignore else
            layer.NextLayer(context)
        )

    def _handle_event(self, event: events.Event) -> layer.CommandGenerator[None]:
        yield from self.child_layer.handle_event(event)


class RawQuicLayer(layer.Layer):
    """
    This layer is responsible for de-multiplexing QUIC streams into an individual layer stack per stream.
    """

    ignore: bool
    """Indicates whether traffic should be routed as-is."""
    datagram_layer: layer.Layer
    """
    The layer that is handling datagrams over QUIC. It's like a child_layer, but with a forked context.
    Instead of having a datagram-equivalent for all `QuicStream*` classes, we use `SendData` and `DataReceived` instead.
    There is also no need for another `NextLayer` marker, as a missing `QuicStreamLayer` implies UDP,
    and the connection state is the same as the one of the underlying QUIC connection.
    """
    client_stream_ids: dict[int, QuicStreamLayer]
    """Maps stream IDs from the client connection to stream layers."""
    server_stream_ids: dict[int, QuicStreamLayer]
    """Maps stream IDs from the server connection to stream layers."""
    connections: dict[connection.Connection, layer.Layer]
    """Maps connections to layers."""
    command_sources: dict[commands.Command, layer.Layer]
    """Keeps track of blocking commands and wakeup requests."""
    next_stream_id: list[int]
    """List containing the next stream ID for all four is_unidirectional/is_client combinations."""

    def __init__(self, context: context.Context, ignore: bool = False) -> None:
        super().__init__(context)
        self.ignore = ignore
        self.datagram_layer = (
            UDPLayer(self.context.fork(), ignore=True)
            if ignore else
            layer.NextLayer(self.context.fork())
        )
        self.client_stream_ids = {}
        self.server_stream_ids = {}
        self.connections = {
            context.client: self.datagram_layer,
            context.server: self.datagram_layer,
        }
        self.command_sources = {}
        self.next_stream_id = [0, 1, 2, 3]

    def _handle_event(self, event: events.Event) -> layer.CommandGenerator[None]:
        # we treat the datagram layer as child layer, so forward Start
        if isinstance(event, events.Start):
            yield from self.event_to_child(self.datagram_layer, event)

        # properly forward completion events based on their command
        elif isinstance(event, events.CommandCompleted):
            yield from self.event_to_child(self.command_sources.pop(event.command), event)

        # route injected messages based on their connections (prefer client, fallback to server)
        elif isinstance(event, events.MessageInjected):
            if event.flow.client_conn in self.connections:
                yield from self.event_to_child(self.connections[event.flow.client_conn], event)
            elif event.flow.server_conn in self.connections:
                yield from self.event_to_child(self.connections[event.flow.server_conn], event)
            else:
                raise AssertionError(f"Flow not associated: {event.flow!r}")

        # handle stream events targeting this context
        elif (
            isinstance(event, QuicStreamEvent)
            and (
                event.connection is self.context.client
                or event.connection is self.context.server
            )
        ):
            from_client = event.connection is self.context.client

            # fetch or create the layer
            stream_ids = self.client_stream_ids if from_client else self.server_stream_ids
            if event.stream_id in stream_ids:
                stream_layer = stream_ids[event.stream_id]
            else:
                # ensure we haven't just forgotten to register the ID
                assert stream_is_client_initiated(event.stream_id) == from_client

                # for server-initiated streams we need to open the client as well
                if from_client:
                    client_stream_id = event.stream_id
                    server_stream_id = None
                else:
                    client_stream_id = self.get_next_available_stream_id(
                        is_client=False,
                        is_unidirectional=stream_is_unidirectional(event.stream_id),
                    )
                    server_stream_id = event.stream_id

                # create, register and start the layer
                stream_layer = QuicStreamLayer(self.context.fork(), self.ignore, client_stream_id, server_stream_id)
                stream_layer.client.state = get_stream_connection_state(client_stream_id, is_client=False)
                self.client_stream_ids[client_stream_id] = stream_layer
                if server_stream_id is not None:
                    stream_layer.server.timestamp_start = time.time()
                    stream_layer.server.state = get_stream_connection_state(server_stream_id, is_client=True)
                    self.server_stream_ids[server_stream_id] = stream_layer
                self.connections[stream_layer.client] = stream_layer
                self.connections[stream_layer.server] = stream_layer
                yield from self.event_to_child(stream_layer, events.Start())

            # forward data and close events
            conn = stream_layer.client if from_client else stream_layer.server
            if isinstance(event, QuicStreamDataReceived):
                yield from self.event_to_child(stream_layer, events.DataReceived(conn, event.data))
                if event.end_stream:
                    yield from self.close_stream_layer(stream_layer, conn)
            elif isinstance(event, QuicStreamReset):
                if self.debug is not None:
                    yield commands.Log(
                        f"{self.debug}[quic] stream_reset (stream_id={event.stream_id}, error_code={event.error_code})", DEBUG
                    )
                yield from self.close_stream_layer(stream_layer, conn)
            else:
                raise AssertionError(f"Unexpected stream event: {event!r}")

        # handle close events that target this context
        elif (
            isinstance(event, events.ConnectionClosed)
            and (
                event.connection is self.context.client
                or event.connection is self.context.server
            )
        ):
            # copy the connection error
            from_client = event.connection is self.context.client
            close_event = get_connection_error(event.connection)
            if close_event is not None:
                set_connection_error(self.context.server if from_client else self.context.client, close_event)

            # always forward to the datagram layer
            yield from self.event_to_child(self.datagram_layer, event)

            # forward to either the client or server connection of stream layers
            for conn, child_layer in self.connections.items():
                if (
                    isinstance(child_layer, QuicStreamLayer)
                    and ((conn is child_layer.client) if from_client else (conn is child_layer.server))
                ):
                    conn.state &= ~connection.ConnectionState.CAN_WRITE
                    yield from self.close_stream_layer(child_layer, conn)

        # all other connection events are routed to their corresponding layer
        elif isinstance(event, events.ConnectionEvent):
            yield from self.event_to_child(self.connections[event.connection], event)

        else:
            raise AssertionError(f"Unexpected event: {event!r}")

    def close_stream_layer(self, stream_layer: QuicStreamLayer, conn: connection.Connection) -> layer.CommandGenerator[None]:
        """Closes the incoming part of a connection."""

        if conn.state & connection.ConnectionState.CAN_READ:
            conn.state &= ~connection.ConnectionState.CAN_READ
            yield from self.event_to_child(stream_layer, events.ConnectionClosed(conn))

    def event_to_child(self, child_layer: layer.Layer, event: events.Event) -> layer.CommandGenerator[None]:
        """Forwards events to child layers and translates commands."""

        for command in child_layer.handle_event(event):
            # intercept commands for streams connections
            if (
                isinstance(child_layer, QuicStreamLayer)
                and isinstance(command, commands.ConnectionCommand)
                and (
                    command.connection is child_layer.client
                    or command.connection is child_layer.server
                )
            ):
                # get the target connection and stream ID
                to_client = command.connection is child_layer.client
                conn = self.context.client if to_client else self.context.server
                stream_id = child_layer.client_stream_id if to_client else child_layer.server_stream_id

                # write data and check CloseConnection wasn't called before
                if isinstance(command, commands.SendData):
                    assert stream_id is not None
                    assert conn.state & connection.ConnectionState.CAN_WRITE
                    yield SendQuicStreamData(conn, stream_id, command.data)

                # send a FIN and optionally also a STOP frame
                elif isinstance(command, commands.CloseConnection):
                    assert stream_id is not None
                    if conn.state & connection.ConnectionState.CAN_WRITE:
                        conn.state &= ~connection.ConnectionState.CAN_WRITE
                        yield SendQuicStreamData(conn, stream_id, b"", end_stream=True)
                    if not command.half_close:
                        if (
                            stream_is_client_initiated(stream_id) == to_client
                            or not stream_is_unidirectional(stream_id)
                        ):
                            yield StopQuicStream(conn, stream_id, QuicErrorCode.NO_ERROR)
                        yield from self.close_stream_layer(child_layer, conn)

                # open server connections by reserving the next stream ID
                elif isinstance(command, commands.OpenConnection):
                    assert not to_client
                    assert stream_id is None
                    child_layer.server.timestamp_start = time.time()
                    stream_id = self.get_next_available_stream_id(
                        is_client=True,
                        is_unidirectional=stream_is_unidirectional(child_layer.client_stream_id)
                    )
                    child_layer.server_stream_id = stream_id
                    child_layer.server.state = get_stream_connection_state(stream_id, is_client=True)
                    self.server_stream_ids[stream_id] = child_layer
                    yield from self.event_to_child(child_layer, events.OpenConnectionCompleted(command, None))

                else:
                    raise AssertionError(f"Unexpected stream connection command: {command!r}")

            # remember blocking and wakeup commands
            else:
                if command.blocking or isinstance(command, commands.RequestWakeup):
                    self.command_sources[command] = child_layer
                if isinstance(command, commands.OpenConnection):
                    self.connections[command.connection] = child_layer
                yield command

    def get_next_available_stream_id(self, is_client: bool, is_unidirectional: bool = False) -> int:
        index = (int(is_unidirectional) << 1) | int(not is_client)
        stream_id = self.next_stream_id[index]
        self.next_stream_id[index] = stream_id + 4
        return stream_id


class QuicLayer(tunnel.TunnelLayer):
    quic: QuicConnection | None = None
    tls: QuicTlsSettings | None = None

    def __init__(self, context: context.Context, conn: connection.Connection) -> None:
        super().__init__(context, tunnel_connection=conn, conn=conn)
        self.child_layer = layer.NextLayer(self.context, ask_on_start=True)
        self._loop = asyncio.get_event_loop()
        self._wakeup_commands: dict[commands.RequestWakeup, float] = dict()
        self._routes: dict[connection.Address, ConnectionHandler | None] = dict()
        conn.tls = True

    def _handle_event(self, event: events.Event) -> layer.CommandGenerator[None]:
        # turn Wakeup events into empty DataReceived events
        if (
            isinstance(event, events.Wakeup)
            and event.command in self._wakeup_commands
        ):
            assert self.quic
            timer = self._wakeup_commands.pop(event.command)
            if self.quic._state is not QuicConnectionState.TERMINATED:
                self.quic.handle_timer(now=max(timer, self._loop.time()))
                event = events.DataReceived(self.tunnel_connection, b"")
        yield from super()._handle_event(event)

    def _handle_command(self, command: commands.Command) -> layer.CommandGenerator[None]:
        """Turns stream commands into aioquic connection invocations."""

        if (
            isinstance(command, QuicStreamCommand)
            and command.connection is self.conn
        ):
            assert self.quic
            if isinstance(command, SendQuicStreamData):
                self.quic.send_stream_data(command.stream_id, command.data, command.end_stream)
            elif isinstance(command, ResetQuicStream):
                self.quic.reset_stream(command.stream_id, command.error_code)
            elif isinstance(command, StopQuicStream):
                # the stream might have already been closed, check before stopping
                if command.stream_id in self.quic._streams:
                    self.quic.stop_stream(command.stream_id, command.error_code)
            else:
                raise AssertionError(f"Unexpected stream command: {command!r}")
            yield from self.tls_interact()
        else:
            yield from super()._handle_command(command)

    def start_tls(self, original_destination_connection_id: bytes | None) -> layer.CommandGenerator[None]:
        """Initiates the aioquic connection."""

        # must only be called if QUIC is uninitialized
        assert not self.quic
        assert not self.tls

        # query addons to provide the necessary TLS settings
        tls_data = QuicTlsData(self.conn, self.context)
        if self.conn is self.context.client:
            yield QuicStartClientHook(tls_data)
        else:
            yield QuicStartServerHook(tls_data)
        if tls_data.settings is None:
            yield commands.Log(f"No QUIC context was provided, failing connection.", ERROR)
            yield commands.CloseConnection(self.conn)
            return

        # build the aioquic connection
        configuration = QuicConfiguration(
            alpn_protocols=(
                [offer.decode("ascii") for offer in self.conn.alpn_offers]
                if self.conn.alpn_offers else
                H3_ALPN
            ),
            is_client=self.conn is self.context.server,
            secrets_log_file=(
                QuicSecretsLogger(tls.log_master_secret)  # type: ignore
                if tls.log_master_secret is not None
                else None
            ),
            server_name=self.conn.sni,
            cafile=tls_data.settings.ca_file,
            capath=tls_data.settings.ca_path,
            certificate=tls_data.settings.certificate,
            certificate_chain=tls_data.settings.certificate_chain,
            cipher_suites=tls_data.settings.cipher_suites,
            private_key=tls_data.settings.certificate_private_key,
            verify_mode=tls_data.settings.verify_mode,
        )
        self.quic = QuicConnection(
            configuration=configuration,
            original_destination_connection_id=original_destination_connection_id,
        )
        self.tls = tls_data.settings

        # if we act as client, connect to upstream
        if original_destination_connection_id is None:
            self.quic.connect(self.conn.peername, now=self._loop.time())
            yield from self.tls_interact()

    def tls_interact(self) -> layer.CommandGenerator[None]:
        """Retrieves all pending outgoing packets from aioquic and sends the data."""

        # send all queued datagrams
        assert self.quic
        for data, addr in self.quic.datagrams_to_send(now=self._loop.time()):
            assert addr == self.conn.peername
            yield commands.SendData(self.tunnel_connection, data)

        # request a new wakeup if all pending requests trigger at a later time
        timer = self.quic.get_timer()
        if (
            timer is not None
            and not any(existing <= timer for existing in self._wakeup_commands.values())
        ):
            command = commands.RequestWakeup(timer - self._loop.time())
            self._wakeup_commands[command] = timer
            yield command

    def receive_handshake_data(self, data: bytes) -> layer.CommandGenerator[tuple[bool, str | None]]:
        assert self.quic

        # forward incoming data to aioquic
        if data:
            self.quic.receive_datagram(data, self.conn.peername, now=self._loop.time())

        # handle pre-handshake events
        while event := self.quic.next_event():
            if isinstance(event, quic_events.ConnectionTerminated):
                err = event.reason_phrase or error_code_to_str(event.error_code)
                return False, err
            elif isinstance(event, quic_events.HandshakeCompleted):
                # concatenate all peer certificates
                all_certs: list[x509.Certificate] = []
                if self.quic.tls._peer_certificate is not None:
                    all_certs.append(self.quic.tls._peer_certificate)
                if self.quic.tls._peer_certificate_chain is not None:
                    all_certs.extend(self.quic.tls._peer_certificate_chain)

                # set the connection's TLS properties
                self.conn.timestamp_tls_setup = self._loop.time()
                if event.alpn_protocol:
                    self.conn.alpn = event.alpn_protocol.encode("ascii")
                self.conn.certificate_list = [certs.Cert(cert) for cert in all_certs]
                assert self.quic.tls.key_schedule
                self.conn.cipher = self.quic.tls.key_schedule.cipher_suite.name
                self.conn.tls_version = "QUIC"

                # log the result and report the success to addons
                if self.debug:
                    yield commands.Log(
                        f"{self.debug}[quic] tls established: {self.conn}", DEBUG
                    )
                if self.conn is self.context.client:
                    yield TlsEstablishedClientHook(QuicTlsData(self.conn, self.context, settings=self.tls))
                else:
                    yield TlsEstablishedServerHook(QuicTlsData(self.conn, self.context, settings=self.tls))

                yield from self.tls_interact()
                return True, None
            elif isinstance(event, (
                quic_events.ConnectionIdIssued,
                quic_events.ConnectionIdRetired,
                quic_events.PingAcknowledged,
                quic_events.ProtocolNegotiated,
            )):
                pass
            else:
                raise AssertionError(f"Unexpected event: {event!r}")

        # transmit buffered data and re-arm timer
        yield from self.tls_interact()
        return False, None

    def on_handshake_error(self, err: str) -> layer.CommandGenerator[None]:
        self.conn.error = err
        if self.conn is self.context.client:
            yield TlsFailedClientHook(QuicTlsData(self.conn, self.context, settings=self.tls))
        else:
            yield TlsFailedServerHook(QuicTlsData(self.conn, self.context, settings=self.tls))
        yield from super().on_handshake_error(err)

    def receive_data(self, data: bytes) -> layer.CommandGenerator[None]:
        assert self.quic

        # forward incoming data to aioquic
        if data:
            self.quic.receive_datagram(data, self.conn.peername, now=self._loop.time())

        # handle post-handshake events
        while event := self.quic.next_event():
            if isinstance(event, quic_events.ConnectionTerminated):
                set_connection_error(self.conn, event)
                if self.debug:
                    reason = event.reason_phrase or error_code_to_str(event.error_code)
                    yield commands.Log(
                        f"{self.debug}[quic] close_notify {self.conn} (reason={reason})", DEBUG
                    )
                yield commands.CloseConnection(self.conn)
                return  # we don't handle any further events, nor do/can we transmit data, so exit
            elif isinstance(event, quic_events.DatagramFrameReceived):
                yield from self.event_to_child(events.DataReceived(self.conn, event.data))
            elif isinstance(event, quic_events.StreamDataReceived):
                yield from self.event_to_child(QuicStreamDataReceived(self.conn, event.stream_id, event.data, event.end_stream))
            elif isinstance(event, quic_events.StreamReset):
                yield from self.event_to_child(QuicStreamReset(self.conn, event.stream_id, event.error_code))
            elif isinstance(event, (
                quic_events.ConnectionIdIssued,
                quic_events.ConnectionIdRetired,
                quic_events.PingAcknowledged,
            )):
                pass
            else:
                raise AssertionError(f"Unexpected event: {event!r}")

        # transmit buffered data and re-arm timer
        yield from self.tls_interact()

    def receive_close(self) -> layer.CommandGenerator[None]:
        # unlike TLS we haven't sent CloseConnection before
        yield from super().receive_close()

    def send_data(self, data: bytes) -> layer.CommandGenerator[None]:
        # non-stream data uses datagram frames
        assert self.quic
        if data:
            self.quic.send_datagram_frame(data)
        yield from self.tls_interact()

    def send_close(self, half_close: bool) -> layer.CommandGenerator[None]:
        # properly close the QUIC connection
        if self.quic is not None:
            close_event = get_connection_error(self.conn)
            if close_event is None:
                self.quic.close()
            else:
                self.quic.close(close_event.error_code, close_event.frame_type, close_event.reason_phrase)
            yield from self.tls_interact()
        yield from super().send_close(half_close)


class ServerQuicLayer(QuicLayer):
    """
    This layer establishes QUIC for a single server connection.
    """

    wait_for_clienthello: bool = False

    def __init__(self, context: context.Context, conn: connection.Server | None = None):
        super().__init__(context, conn or context.server)

    def start_handshake(self) -> layer.CommandGenerator[None]:
        wait_for_clienthello = (
            not self.command_to_reply_to
            and isinstance(self.child_layer, ClientQuicLayer)
        )
        if wait_for_clienthello:
            self.wait_for_clienthello = True
            self.tunnel_state = tunnel.TunnelState.CLOSED
        else:
            yield from self.start_tls(None)

    def event_to_child(self, event: events.Event) -> layer.CommandGenerator[None]:
        if self.wait_for_clienthello:
            for command in super().event_to_child(event):
                if (
                    isinstance(command, commands.OpenConnection)
                    and command.connection == self.conn
                ):
                    self.wait_for_clienthello = False
                else:
                    yield command
        else:
            yield from super().event_to_child(event)

    def on_handshake_error(self, err: str) -> layer.CommandGenerator[None]:
        yield commands.Log(f"Server QUIC handshake failed. {err}", level=WARNING)
        yield from super().on_handshake_error(err)


class ClientQuicLayer(QuicLayer):
    """
    This layer establishes QUIC on a single client connection or roams to another connection.
    """

    server_tls_available: bool
    """Indicates whether the parent layer is a ServerQuicLayer."""

    def __init__(self, context: context.Context) -> None:
        # same as ClientTLSLayer, we might be nested in some other transport
        if context.client.tls:
            context.client.alpn = None
            context.client.cipher = None
            context.client.sni = None
            context.client.timestamp_tls_setup = None
            context.client.tls_version = None
            context.client.certificate_list = []
            context.client.mitmcert = None
            context.client.alpn_offers = []
            context.client.cipher_list = []

        super().__init__(context, context.client)
        self.server_tls_available = isinstance(self.context.layers[-2], ServerQuicLayer)

    def start_handshake(self) -> layer.CommandGenerator[None]:
        yield from ()

    def receive_handshake_data(self, data: bytes) -> layer.CommandGenerator[tuple[bool, str | None]]:
        # if we already had a valid client hello, don't process further packets
        if self.tls is not None:
            return (yield from super().receive_handshake_data(data))

        # fail if the received data is not a QUIC packet
        buffer = QuicBuffer(data=data)
        try:
            header = pull_quic_header(buffer)
        except ValueError as e:
            return False, f"Cannot parse QUIC header: {e} ({data.hex()})"

        # negotiate version, support all versions known to aioquic
        supported_versions = [
            version.value
            for version in QuicProtocolVersion
            if version is not QuicProtocolVersion.NEGOTIATION
        ]
        if header.version is not None and header.version not in supported_versions:
            yield commands.SendData(
                self.tunnel_connection,
                encode_quic_version_negotiation(
                    source_cid=header.destination_cid,
                    destination_cid=header.source_cid,
                    supported_versions=supported_versions,
                ),
            )
            return False, None

        # ensure it's (likely) a client handshake packet
        if len(data) < 1200 or header.packet_type != PACKET_TYPE_INITIAL:
            return False, f"Invalid handshake received, roaming not supported. ({data.hex()})"

        # extract the client hello
        try:
            client_hello = quic_parse_client_hello(data)
        except ValueError as e:
            return False, f"Cannot parse ClientHello: {str(e)} ({data.hex()})"

        # copy the client hello information
        self.context.client.sni = client_hello.sni
        self.context.client.alpn_offers = client_hello.alpn_protocols

        # check with addons what we shall do
        tls_clienthello = ClientHelloData(self.context, client_hello)
        yield TlsClienthelloHook(tls_clienthello)

        # replace the QUIC layer with an UDP layer if requested
        if tls_clienthello.ignore_connection:
            self.conn = self.tunnel_connection = connection.Client(
                ("ignore-conn", 0), ("ignore-conn", 0), self._loop.time(),
                transport_protocol="udp", proxy_mode=self.context.client.proxy_mode
            )

            # we need to replace the server layer as well, if there is one
            parent_layer = self.context.layers[self.context.layers.index(self) - 1]
            if isinstance(parent_layer, ServerQuicLayer):
                parent_layer.conn = parent_layer.tunnel_connection = connection.Server(
                    None
                )
            replacement_layer = UDPLayer(self.context, ignore=True)
            parent_layer.handle_event = replacement_layer.handle_event  # type: ignore
            parent_layer._handle_event = replacement_layer._handle_event  # type: ignore
            yield from parent_layer.handle_event(events.Start())
            yield from parent_layer.handle_event(events.DataReceived(self.conn, data))
            return True, None

        # start the server QUIC connection if demanded and available
        if (
            tls_clienthello.establish_server_tls_first
            and not self.context.server.tls_established
        ):
            err = yield from self.start_server_tls()
            if err:
                yield commands.Log(
                    f"Unable to establish QUIC connection with server ({err}). "
                    f"Trying to establish QUIC with client anyway. "
                    f"If you plan to redirect requests away from this server, "
                    f"consider setting `connection_strategy` to `lazy` to suppress early connections."
                )

        # start the client QUIC connection
        yield from self.start_tls(header.destination_cid)
        if not self.conn.connected:
            return False, "connection closed early"

        # send the client hello to aioquic
        return (yield from super().receive_handshake_data(data))

    def start_server_tls(self) -> layer.CommandGenerator[str | None]:
        if not self.server_tls_available:
            return f"No server QUIC available."
        err = yield commands.OpenConnection(self.context.server)
        return err

    def on_handshake_error(self, err: str) -> layer.CommandGenerator[None]:
        yield commands.Log(f"Client QUIC handshake failed. {err}", level=WARNING)
        yield from super().on_handshake_error(err)
        self.event_to_child = self.errored  # type: ignore

    def errored(self, event: events.Event) -> layer.CommandGenerator[None]:
        if self.debug is not None:
            yield commands.Log(f"{self.debug}[quic] Swallowing {event} as handshake failed.", DEBUG)
