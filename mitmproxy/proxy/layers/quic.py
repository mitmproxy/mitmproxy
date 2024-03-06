from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from dataclasses import field
from logging import DEBUG
from logging import ERROR
from logging import WARNING
from ssl import VerifyMode

from aioquic.buffer import Buffer as QuicBuffer
from aioquic.h3.connection import ErrorCode as H3ErrorCode
from aioquic.quic import events as quic_events
from aioquic.quic.configuration import QuicConfiguration
from aioquic.quic.connection import QuicConnection
from aioquic.quic.connection import QuicConnectionError
from aioquic.quic.connection import QuicConnectionState
from aioquic.quic.connection import QuicErrorCode
from aioquic.quic.connection import stream_is_client_initiated
from aioquic.quic.connection import stream_is_unidirectional
from aioquic.quic.packet import encode_quic_version_negotiation
from aioquic.quic.packet import PACKET_TYPE_INITIAL
from aioquic.quic.packet import pull_quic_header
from aioquic.quic.packet import QuicProtocolVersion
from aioquic.tls import CipherSuite
from aioquic.tls import HandshakeType
from cryptography import x509
from cryptography.hazmat.primitives.asymmetric import dsa
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric import rsa

from mitmproxy import certs
from mitmproxy import connection
from mitmproxy import ctx
from mitmproxy.net import tls
from mitmproxy.proxy import commands
from mitmproxy.proxy import context
from mitmproxy.proxy import events
from mitmproxy.proxy import layer
from mitmproxy.proxy import tunnel
from mitmproxy.proxy.layers.modes import TransparentProxy
from mitmproxy.proxy.layers.tcp import TCPLayer
from mitmproxy.proxy.layers.tls import TlsClienthelloHook
from mitmproxy.proxy.layers.tls import TlsEstablishedClientHook
from mitmproxy.proxy.layers.tls import TlsEstablishedServerHook
from mitmproxy.proxy.layers.tls import TlsFailedClientHook
from mitmproxy.proxy.layers.tls import TlsFailedServerHook
from mitmproxy.proxy.layers.udp import UDPLayer
from mitmproxy.tls import ClientHello
from mitmproxy.tls import ClientHelloData
from mitmproxy.tls import TlsData


@dataclass
class QuicTlsSettings:
    """
    Settings necessary to establish QUIC's TLS context.
    """

    alpn_protocols: list[str] | None = None
    """A list of supported ALPN protocols."""
    certificate: x509.Certificate | None = None
    """The certificate to use for the connection."""
    certificate_chain: list[x509.Certificate] = field(default_factory=list)
    """A list of additional certificates to send to the peer."""
    certificate_private_key: (
        dsa.DSAPrivateKey | ec.EllipticCurvePrivateKey | rsa.RSAPrivateKey | None
    ) = None
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

    def __repr__(self):
        target = type(self.connection).__name__.lower()
        end_stream = "[end_stream] " if self.end_stream else ""
        return f"QuicStreamDataReceived({target} on {self.stream_id}, {end_stream}{self.data!r})"


@dataclass
class QuicStreamReset(QuicStreamEvent):
    """Event that is fired when the remote peer resets a stream."""

    error_code: int
    """The error code that triggered the reset."""


class QuicStreamCommand(commands.ConnectionCommand):
    """Base class for all QUIC stream commands."""

    stream_id: int
    """The ID of the stream the command was issued for."""

    def __init__(self, connection: connection.Connection, stream_id: int) -> None:
        super().__init__(connection)
        self.stream_id = stream_id


class SendQuicStreamData(QuicStreamCommand):
    """Command that sends data on a stream."""

    data: bytes
    """The data which should be sent."""
    end_stream: bool
    """Whether the FIN bit should be set in the STREAM frame."""

    def __init__(
        self,
        connection: connection.Connection,
        stream_id: int,
        data: bytes,
        end_stream: bool = False,
    ) -> None:
        super().__init__(connection, stream_id)
        self.data = data
        self.end_stream = end_stream

    def __repr__(self):
        target = type(self.connection).__name__.lower()
        end_stream = "[end_stream] " if self.end_stream else ""
        return f"SendQuicStreamData({target} on {self.stream_id}, {end_stream}{self.data!r})"


class ResetQuicStream(QuicStreamCommand):
    """Abruptly terminate the sending part of a stream."""

    error_code: int
    """An error code indicating why the stream is being reset."""

    def __init__(
        self, connection: connection.Connection, stream_id: int, error_code: int
    ) -> None:
        super().__init__(connection, stream_id)
        self.error_code = error_code


class StopQuicStream(QuicStreamCommand):
    """Request termination of the receiving part of a stream."""

    error_code: int
    """An error code indicating why the stream is being stopped."""

    def __init__(
        self, connection: connection.Connection, stream_id: int, error_code: int
    ) -> None:
        super().__init__(connection, stream_id)
        self.error_code = error_code


class CloseQuicConnection(commands.CloseConnection):
    """Close a QUIC connection."""

    error_code: int
    "The error code which was specified when closing the connection."

    frame_type: int | None
    "The frame type which caused the connection to be closed, or `None`."

    reason_phrase: str
    "The human-readable reason for which the connection was closed."

    # XXX: A bit much boilerplate right now. Should switch to dataclasses.
    def __init__(
        self,
        conn: connection.Connection,
        error_code: int,
        frame_type: int | None,
        reason_phrase: str,
    ) -> None:
        super().__init__(conn)
        self.error_code = error_code
        self.frame_type = frame_type
        self.reason_phrase = reason_phrase


class QuicConnectionClosed(events.ConnectionClosed):
    """QUIC connection has been closed."""

    error_code: int
    "The error code which was specified when closing the connection."

    frame_type: int | None
    "The frame type which caused the connection to be closed, or `None`."

    reason_phrase: str
    "The human-readable reason for which the connection was closed."

    def __init__(
        self,
        conn: connection.Connection,
        error_code: int,
        frame_type: int | None,
        reason_phrase: str,
    ) -> None:
        super().__init__(conn)
        self.error_code = error_code
        self.frame_type = frame_type
        self.reason_phrase = reason_phrase


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


def is_success_error_code(error_code: int) -> bool:
    """Returns whether the given error code actually indicates no error."""

    return error_code in (QuicErrorCode.NO_ERROR, H3ErrorCode.H3_NO_ERROR)


def tls_settings_to_configuration(
    settings: QuicTlsSettings,
    is_client: bool,
    server_name: str | None = None,
) -> QuicConfiguration:
    """Converts `QuicTlsSettings` to `QuicConfiguration`."""

    return QuicConfiguration(
        alpn_protocols=settings.alpn_protocols,
        is_client=is_client,
        secrets_log_file=(
            QuicSecretsLogger(tls.log_master_secret)  # type: ignore
            if tls.log_master_secret is not None
            else None
        ),
        server_name=server_name,
        cafile=settings.ca_file,
        capath=settings.ca_path,
        certificate=settings.certificate,
        certificate_chain=settings.certificate_chain,
        cipher_suites=settings.cipher_suites,
        private_key=settings.certificate_private_key,
        verify_mode=settings.verify_mode,
        max_datagram_frame_size=65536,
    )


@dataclass
class QuicClientHello(Exception):
    """Helper error only used in `quic_parse_client_hello`."""

    data: bytes


def quic_parse_client_hello(data: bytes) -> ClientHello:
    """Helper function that parses a client hello packet."""

    # ensure the first packet is indeed the initial one
    buffer = QuicBuffer(data=data)
    header = pull_quic_header(buffer, 8)
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


class QuicStreamNextLayer(layer.NextLayer):
    """`NextLayer` variant that callbacks `QuicStreamLayer` after layer decision."""

    def __init__(
        self,
        context: context.Context,
        stream: QuicStreamLayer,
        ask_on_start: bool = False,
    ) -> None:
        super().__init__(context, ask_on_start)
        self._stream = stream
        self._layer: layer.Layer | None = None

    @property  # type: ignore
    def layer(self) -> layer.Layer | None:  # type: ignore
        return self._layer

    @layer.setter
    def layer(self, value: layer.Layer | None) -> None:
        self._layer = value
        if self._layer:
            self._stream.refresh_metadata()


class QuicStreamLayer(layer.Layer):
    """
    Layer for QUIC streams.
    Serves as a marker for NextLayer and keeps track of the connection states.
    """

    client: connection.Client
    """Virtual client connection for this stream. Use this in QuicRawLayer instead of `context.client`."""
    server: connection.Server
    """Virtual server connection for this stream. Use this in QuicRawLayer instead of `context.server`."""
    child_layer: layer.Layer
    """The stream's child layer."""

    def __init__(self, context: context.Context, ignore: bool, stream_id: int) -> None:
        # we mustn't reuse the client from the QUIC connection, as the state and protocol differs
        self.client = context.client = context.client.copy()
        self.client.transport_protocol = "tcp"
        self.client.state = connection.ConnectionState.OPEN

        # unidirectional client streams are not fully open, set the appropriate state
        if stream_is_unidirectional(stream_id):
            self.client.state = (
                connection.ConnectionState.CAN_READ
                if stream_is_client_initiated(stream_id)
                else connection.ConnectionState.CAN_WRITE
            )
        self._client_stream_id = stream_id

        # start with a closed server
        self.server = context.server = connection.Server(
            address=context.server.address,
            transport_protocol="tcp",
        )
        self._server_stream_id: int | None = None

        # ignored connections will be assigned a TCPLayer immediately
        super().__init__(context)
        self.child_layer = (
            TCPLayer(context, ignore=True)
            if ignore
            else QuicStreamNextLayer(context, self)
        )
        self.refresh_metadata()

        # we don't handle any events, pass everything to the child layer
        self.handle_event = self.child_layer.handle_event  # type: ignore
        self._handle_event = self.child_layer._handle_event  # type: ignore

    def _handle_event(self, event: events.Event) -> layer.CommandGenerator[None]:
        raise AssertionError  # pragma: no cover

    def open_server_stream(self, server_stream_id) -> None:
        assert self._server_stream_id is None
        self._server_stream_id = server_stream_id
        self.server.timestamp_start = time.time()
        self.server.state = (
            (
                connection.ConnectionState.CAN_WRITE
                if stream_is_client_initiated(server_stream_id)
                else connection.ConnectionState.CAN_READ
            )
            if stream_is_unidirectional(server_stream_id)
            else connection.ConnectionState.OPEN
        )
        self.refresh_metadata()

    def refresh_metadata(self) -> None:
        # find the first transport layer
        child_layer: layer.Layer | None = self.child_layer
        while True:
            if isinstance(child_layer, layer.NextLayer):
                child_layer = child_layer.layer
            elif isinstance(child_layer, tunnel.TunnelLayer):
                child_layer = child_layer.child_layer
            else:
                break  # pragma: no cover
        if isinstance(child_layer, (UDPLayer, TCPLayer)) and child_layer.flow:
            child_layer.flow.metadata["quic_is_unidirectional"] = (
                stream_is_unidirectional(self._client_stream_id)
            )
            child_layer.flow.metadata["quic_initiator"] = (
                "client"
                if stream_is_client_initiated(self._client_stream_id)
                else "server"
            )
            child_layer.flow.metadata["quic_stream_id_client"] = self._client_stream_id
            child_layer.flow.metadata["quic_stream_id_server"] = self._server_stream_id

    def stream_id(self, client: bool) -> int | None:
        return self._client_stream_id if client else self._server_stream_id


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
            if ignore
            else layer.NextLayer(self.context.fork())
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
            if self.context.server.timestamp_start is None:
                err = yield commands.OpenConnection(self.context.server)
                if err:
                    yield commands.CloseConnection(self.context.client)
                    self._handle_event = self.done  # type: ignore
                    return
            yield from self.event_to_child(self.datagram_layer, event)

        # properly forward completion events based on their command
        elif isinstance(event, events.CommandCompleted):
            yield from self.event_to_child(
                self.command_sources.pop(event.command), event
            )

        # route injected messages based on their connections (prefer client, fallback to server)
        elif isinstance(event, events.MessageInjected):
            if event.flow.client_conn in self.connections:
                yield from self.event_to_child(
                    self.connections[event.flow.client_conn], event
                )
            elif event.flow.server_conn in self.connections:
                yield from self.event_to_child(
                    self.connections[event.flow.server_conn], event
                )
            else:
                raise AssertionError(f"Flow not associated: {event.flow!r}")

        # handle stream events targeting this context
        elif isinstance(event, QuicStreamEvent) and (
            event.connection is self.context.client
            or event.connection is self.context.server
        ):
            from_client = event.connection is self.context.client

            # fetch or create the layer
            stream_ids = (
                self.client_stream_ids if from_client else self.server_stream_ids
            )
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
                stream_layer = QuicStreamLayer(
                    self.context.fork(), self.ignore, client_stream_id
                )
                self.client_stream_ids[client_stream_id] = stream_layer
                if server_stream_id is not None:
                    stream_layer.open_server_stream(server_stream_id)
                    self.server_stream_ids[server_stream_id] = stream_layer
                self.connections[stream_layer.client] = stream_layer
                self.connections[stream_layer.server] = stream_layer
                yield from self.event_to_child(stream_layer, events.Start())

            # forward data and close events
            conn = stream_layer.client if from_client else stream_layer.server
            if isinstance(event, QuicStreamDataReceived):
                if event.data:
                    yield from self.event_to_child(
                        stream_layer, events.DataReceived(conn, event.data)
                    )
                if event.end_stream:
                    yield from self.close_stream_layer(stream_layer, from_client)
            elif isinstance(event, QuicStreamReset):
                # preserve stream resets
                for command in self.close_stream_layer(stream_layer, from_client):
                    if (
                        isinstance(command, SendQuicStreamData)
                        and command.stream_id == stream_layer.stream_id(not from_client)
                        and command.end_stream
                        and not command.data
                    ):
                        yield ResetQuicStream(
                            command.connection, command.stream_id, event.error_code
                        )
                    else:
                        yield command
            else:
                raise AssertionError(f"Unexpected stream event: {event!r}")

        # handle close events that target this context
        elif isinstance(event, QuicConnectionClosed) and (
            event.connection is self.context.client
            or event.connection is self.context.server
        ):
            from_client = event.connection is self.context.client
            other_conn = self.context.server if from_client else self.context.client

            # be done if both connections are closed
            if other_conn.connected:
                yield CloseQuicConnection(
                    other_conn, event.error_code, event.frame_type, event.reason_phrase
                )
            else:
                self._handle_event = self.done  # type: ignore

            # always forward to the datagram layer and swallow `CloseConnection` commands
            for command in self.event_to_child(self.datagram_layer, event):
                if (
                    not isinstance(command, commands.CloseConnection)
                    or command.connection is not other_conn
                ):
                    yield command

            # forward to either the client or server connection of stream layers and swallow empty stream end
            for conn, child_layer in self.connections.items():
                if isinstance(child_layer, QuicStreamLayer) and (
                    (conn is child_layer.client)
                    if from_client
                    else (conn is child_layer.server)
                ):
                    conn.state &= ~connection.ConnectionState.CAN_WRITE
                    for command in self.close_stream_layer(child_layer, from_client):
                        if not isinstance(command, SendQuicStreamData) or command.data:
                            yield command

        # all other connection events are routed to their corresponding layer
        elif isinstance(event, events.ConnectionEvent):
            yield from self.event_to_child(self.connections[event.connection], event)

        else:
            raise AssertionError(f"Unexpected event: {event!r}")

    def close_stream_layer(
        self, stream_layer: QuicStreamLayer, client: bool
    ) -> layer.CommandGenerator[None]:
        """Closes the incoming part of a connection."""

        conn = stream_layer.client if client else stream_layer.server
        conn.state &= ~connection.ConnectionState.CAN_READ
        assert conn.timestamp_start is not None
        if conn.timestamp_end is None:
            conn.timestamp_end = time.time()
            yield from self.event_to_child(stream_layer, events.ConnectionClosed(conn))

    def event_to_child(
        self, child_layer: layer.Layer, event: events.Event
    ) -> layer.CommandGenerator[None]:
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
                quic_conn = self.context.client if to_client else self.context.server
                stream_id = child_layer.stream_id(to_client)

                # write data and check CloseConnection wasn't called before
                if isinstance(command, commands.SendData):
                    assert stream_id is not None
                    if command.connection.state & connection.ConnectionState.CAN_WRITE:
                        yield SendQuicStreamData(quic_conn, stream_id, command.data)

                # send a FIN and optionally also a STOP frame
                elif isinstance(command, commands.CloseConnection):
                    assert stream_id is not None
                    if command.connection.state & connection.ConnectionState.CAN_WRITE:
                        command.connection.state &= (
                            ~connection.ConnectionState.CAN_WRITE
                        )
                        yield SendQuicStreamData(
                            quic_conn, stream_id, b"", end_stream=True
                        )
                    # XXX: Use `command.connection.state & connection.ConnectionState.CAN_READ` instead?
                    only_close_our_half = (
                        isinstance(command, commands.CloseTcpConnection)
                        and command.half_close
                    )
                    if not only_close_our_half:
                        if stream_is_client_initiated(
                            stream_id
                        ) == to_client or not stream_is_unidirectional(stream_id):
                            yield StopQuicStream(
                                quic_conn, stream_id, QuicErrorCode.NO_ERROR
                            )
                        yield from self.close_stream_layer(child_layer, to_client)

                # open server connections by reserving the next stream ID
                elif isinstance(command, commands.OpenConnection):
                    assert not to_client
                    assert stream_id is None
                    client_stream_id = child_layer.stream_id(client=True)
                    assert client_stream_id is not None
                    stream_id = self.get_next_available_stream_id(
                        is_client=True,
                        is_unidirectional=stream_is_unidirectional(client_stream_id),
                    )
                    child_layer.open_server_stream(stream_id)
                    self.server_stream_ids[stream_id] = child_layer
                    yield from self.event_to_child(
                        child_layer, events.OpenConnectionCompleted(command, None)
                    )

                else:
                    raise AssertionError(
                        f"Unexpected stream connection command: {command!r}"
                    )

            # remember blocking and wakeup commands
            else:
                if command.blocking or isinstance(command, commands.RequestWakeup):
                    self.command_sources[command] = child_layer
                if isinstance(command, commands.OpenConnection):
                    self.connections[command.connection] = child_layer
                yield command

    def get_next_available_stream_id(
        self, is_client: bool, is_unidirectional: bool = False
    ) -> int:
        index = (int(is_unidirectional) << 1) | int(not is_client)
        stream_id = self.next_stream_id[index]
        self.next_stream_id[index] = stream_id + 4
        return stream_id

    def done(self, _) -> layer.CommandGenerator[None]:  # pragma: no cover
        yield from ()


class QuicLayer(tunnel.TunnelLayer):
    quic: QuicConnection | None = None
    tls: QuicTlsSettings | None = None

    def __init__(
        self,
        context: context.Context,
        conn: connection.Connection,
        time: Callable[[], float] | None,
    ) -> None:
        super().__init__(context, tunnel_connection=conn, conn=conn)
        self.child_layer = layer.NextLayer(self.context, ask_on_start=True)
        self._time = time or ctx.master.event_loop.time
        self._wakeup_commands: dict[commands.RequestWakeup, float] = dict()
        conn.tls = True

    def _handle_event(self, event: events.Event) -> layer.CommandGenerator[None]:
        if isinstance(event, events.Wakeup) and event.command in self._wakeup_commands:
            # TunnelLayer has no understanding of wakeups, so we turn this into an empty DataReceived event
            # which TunnelLayer recognizes as belonging to our connection.
            assert self.quic
            scheduled_time = self._wakeup_commands.pop(event.command)
            if self.quic._state is not QuicConnectionState.TERMINATED:
                # weird quirk: asyncio sometimes returns a bit ahead of time.
                now = max(scheduled_time, self._time())
                self.quic.handle_timer(now)
                yield from super()._handle_event(
                    events.DataReceived(self.tunnel_connection, b"")
                )
        else:
            yield from super()._handle_event(event)

    def event_to_child(self, event: events.Event) -> layer.CommandGenerator[None]:
        # the parent will call _handle_command multiple times, we transmit cumulative afterwards
        # this will reduce the number of sends, especially if data=b"" and end_stream=True
        yield from super().event_to_child(event)
        if self.quic:
            yield from self.tls_interact()

    def _handle_command(
        self, command: commands.Command
    ) -> layer.CommandGenerator[None]:
        """Turns stream commands into aioquic connection invocations."""
        if isinstance(command, QuicStreamCommand) and command.connection is self.conn:
            assert self.quic
            if isinstance(command, SendQuicStreamData):
                self.quic.send_stream_data(
                    command.stream_id, command.data, command.end_stream
                )
            elif isinstance(command, ResetQuicStream):
                self.quic.reset_stream(command.stream_id, command.error_code)
            elif isinstance(command, StopQuicStream):
                # the stream might have already been closed, check before stopping
                if command.stream_id in self.quic._streams:
                    self.quic.stop_stream(command.stream_id, command.error_code)
            else:
                raise AssertionError(f"Unexpected stream command: {command!r}")
        else:
            yield from super()._handle_command(command)

    def start_tls(
        self, original_destination_connection_id: bytes | None
    ) -> layer.CommandGenerator[None]:
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
        if not tls_data.settings:
            yield commands.Log(
                f"No QUIC context was provided, failing connection.", ERROR
            )
            yield commands.CloseConnection(self.conn)
            return

        # build the aioquic connection
        configuration = tls_settings_to_configuration(
            settings=tls_data.settings,
            is_client=self.conn is self.context.server,
            server_name=self.conn.sni,
        )
        self.quic = QuicConnection(
            configuration=configuration,
            original_destination_connection_id=original_destination_connection_id,
        )
        self.tls = tls_data.settings

        # if we act as client, connect to upstream
        if original_destination_connection_id is None:
            self.quic.connect(self.conn.peername, now=self._time())
            yield from self.tls_interact()

    def tls_interact(self) -> layer.CommandGenerator[None]:
        """Retrieves all pending outgoing packets from aioquic and sends the data."""

        # send all queued datagrams
        assert self.quic
        now = self._time()

        for data, addr in self.quic.datagrams_to_send(now=now):
            assert addr == self.conn.peername
            yield commands.SendData(self.tunnel_connection, data)

        timer = self.quic.get_timer()
        if timer is not None:
            # smooth wakeups a bit.
            smoothed = timer + 0.002
            # request a new wakeup if all pending requests trigger at a later time
            if not any(
                existing <= smoothed for existing in self._wakeup_commands.values()
            ):
                command = commands.RequestWakeup(timer - now)
                self._wakeup_commands[command] = timer
                yield command

    def receive_handshake_data(
        self, data: bytes
    ) -> layer.CommandGenerator[tuple[bool, str | None]]:
        assert self.quic

        # forward incoming data to aioquic
        if data:
            self.quic.receive_datagram(data, self.conn.peername, now=self._time())

        # handle pre-handshake events
        while event := self.quic.next_event():
            if isinstance(event, quic_events.ConnectionTerminated):
                err = event.reason_phrase or error_code_to_str(event.error_code)
                return False, err
            elif isinstance(event, quic_events.HandshakeCompleted):
                # concatenate all peer certificates
                all_certs: list[x509.Certificate] = []
                if self.quic.tls._peer_certificate:
                    all_certs.append(self.quic.tls._peer_certificate)
                all_certs.extend(self.quic.tls._peer_certificate_chain)

                # set the connection's TLS properties
                self.conn.timestamp_tls_setup = time.time()
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
                    yield TlsEstablishedClientHook(
                        QuicTlsData(self.conn, self.context, settings=self.tls)
                    )
                else:
                    yield TlsEstablishedServerHook(
                        QuicTlsData(self.conn, self.context, settings=self.tls)
                    )

                yield from self.tls_interact()
                return True, None
            elif isinstance(
                event,
                (
                    quic_events.ConnectionIdIssued,
                    quic_events.ConnectionIdRetired,
                    quic_events.PingAcknowledged,
                    quic_events.ProtocolNegotiated,
                ),
            ):
                pass
            else:
                raise AssertionError(f"Unexpected event: {event!r}")

        # transmit buffered data and re-arm timer
        yield from self.tls_interact()
        return False, None

    def on_handshake_error(self, err: str) -> layer.CommandGenerator[None]:
        self.conn.error = err
        if self.conn is self.context.client:
            yield TlsFailedClientHook(
                QuicTlsData(self.conn, self.context, settings=self.tls)
            )
        else:
            yield TlsFailedServerHook(
                QuicTlsData(self.conn, self.context, settings=self.tls)
            )
        yield from super().on_handshake_error(err)

    def receive_data(self, data: bytes) -> layer.CommandGenerator[None]:
        assert self.quic

        # forward incoming data to aioquic
        if data:
            self.quic.receive_datagram(data, self.conn.peername, now=self._time())

        # handle post-handshake events
        while event := self.quic.next_event():
            if isinstance(event, quic_events.ConnectionTerminated):
                if self.debug:
                    reason = event.reason_phrase or error_code_to_str(event.error_code)
                    yield commands.Log(
                        f"{self.debug}[quic] close_notify {self.conn} (reason={reason})",
                        DEBUG,
                    )
                # We don't rely on `ConnectionTerminated` to dispatch `QuicConnectionClosed`, because
                # after aioquic receives a termination frame, it still waits for the next `handle_timer`
                # before returning `ConnectionTerminated` in `next_event`. In the meantime, the underlying
                # connection could be closed. Therefore, we instead dispatch on `ConnectionClosed` and simply
                # close the connection here.
                yield commands.CloseConnection(self.tunnel_connection)
                return  # we don't handle any further events, nor do/can we transmit data, so exit
            elif isinstance(event, quic_events.DatagramFrameReceived):
                yield from self.event_to_child(
                    events.DataReceived(self.conn, event.data)
                )
            elif isinstance(event, quic_events.StreamDataReceived):
                yield from self.event_to_child(
                    QuicStreamDataReceived(
                        self.conn, event.stream_id, event.data, event.end_stream
                    )
                )
            elif isinstance(event, quic_events.StreamReset):
                yield from self.event_to_child(
                    QuicStreamReset(self.conn, event.stream_id, event.error_code)
                )
            elif isinstance(
                event,
                (
                    quic_events.ConnectionIdIssued,
                    quic_events.ConnectionIdRetired,
                    quic_events.PingAcknowledged,
                    quic_events.ProtocolNegotiated,
                ),
            ):
                pass
            else:
                raise AssertionError(f"Unexpected event: {event!r}")

        # transmit buffered data and re-arm timer
        yield from self.tls_interact()

    def receive_close(self) -> layer.CommandGenerator[None]:
        assert self.quic
        # if `_close_event` is not set, the underlying connection has been closed
        # we turn this into a QUIC close event as well
        close_event = self.quic._close_event or quic_events.ConnectionTerminated(
            QuicErrorCode.NO_ERROR, None, "Connection closed."
        )
        yield from self.event_to_child(
            QuicConnectionClosed(
                self.conn,
                close_event.error_code,
                close_event.frame_type,
                close_event.reason_phrase,
            )
        )

    def send_data(self, data: bytes) -> layer.CommandGenerator[None]:
        # non-stream data uses datagram frames
        assert self.quic
        if data:
            self.quic.send_datagram_frame(data)
        yield from self.tls_interact()

    def send_close(
        self, command: commands.CloseConnection
    ) -> layer.CommandGenerator[None]:
        # properly close the QUIC connection
        if self.quic:
            if isinstance(command, CloseQuicConnection):
                self.quic.close(
                    command.error_code, command.frame_type, command.reason_phrase
                )
            else:
                self.quic.close()
            yield from self.tls_interact()
        yield from super().send_close(command)


class ServerQuicLayer(QuicLayer):
    """
    This layer establishes QUIC for a single server connection.
    """

    wait_for_clienthello: bool = False

    def __init__(
        self,
        context: context.Context,
        conn: connection.Server | None = None,
        time: Callable[[], float] | None = None,
    ):
        super().__init__(context, conn or context.server, time)

    def start_handshake(self) -> layer.CommandGenerator[None]:
        wait_for_clienthello = not self.command_to_reply_to and isinstance(
            self.child_layer, ClientQuicLayer
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
    This layer establishes QUIC on a single client connection.
    """

    server_tls_available: bool
    """Indicates whether the parent layer is a ServerQuicLayer."""

    def __init__(
        self, context: context.Context, time: Callable[[], float] | None = None
    ) -> None:
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

        super().__init__(context, context.client, time)
        self.server_tls_available = len(self.context.layers) >= 2 and isinstance(
            self.context.layers[-2], ServerQuicLayer
        )

    def start_handshake(self) -> layer.CommandGenerator[None]:
        yield from ()

    def receive_handshake_data(
        self, data: bytes
    ) -> layer.CommandGenerator[tuple[bool, str | None]]:
        if isinstance(self.context.layers[0], TransparentProxy):  # pragma: no cover
            yield commands.Log(
                f"Swallowing QUIC handshake because HTTP/3 does not support transparent mode yet.",
                DEBUG,
            )
            return False, None
        if not self.context.options.http3:
            yield commands.Log(
                f"Swallowing QUIC handshake because HTTP/3 is disabled.", DEBUG
            )
            return False, None

        # if we already had a valid client hello, don't process further packets
        if self.tls:
            return (yield from super().receive_handshake_data(data))

        # fail if the received data is not a QUIC packet
        buffer = QuicBuffer(data=data)
        try:
            header = pull_quic_header(buffer)
        except TypeError:
            return False, f"Cannot parse QUIC header: Malformed head ({data.hex()})"
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
            return (
                False,
                f"Invalid handshake received, roaming not supported. ({data.hex()})",
            )

        # extract the client hello
        try:
            client_hello = quic_parse_client_hello(data)
        except ValueError as e:
            return False, f"Cannot parse ClientHello: {str(e)} ({data.hex()})"

        # copy the client hello information
        self.conn.sni = client_hello.sni
        self.conn.alpn_offers = client_hello.alpn_protocols

        # check with addons what we shall do
        tls_clienthello = ClientHelloData(self.context, client_hello)
        yield TlsClienthelloHook(tls_clienthello)

        # replace the QUIC layer with an UDP layer if requested
        if tls_clienthello.ignore_connection:
            self.conn = self.tunnel_connection = connection.Client(
                peername=("ignore-conn", 0),
                sockname=("ignore-conn", 0),
                transport_protocol="udp",
                state=connection.ConnectionState.OPEN,
            )

            # we need to replace the server layer as well, if there is one
            parent_layer = self.context.layers[self.context.layers.index(self) - 1]
            if isinstance(parent_layer, ServerQuicLayer):
                parent_layer.conn = parent_layer.tunnel_connection = connection.Server(
                    address=None
                )
            replacement_layer = UDPLayer(self.context, ignore=True)
            parent_layer.handle_event = replacement_layer.handle_event  # type: ignore
            parent_layer._handle_event = replacement_layer._handle_event  # type: ignore
            yield from parent_layer.handle_event(events.Start())
            yield from parent_layer.handle_event(
                events.DataReceived(self.context.client, data)
            )
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
        # XXX copied from TLS, we assume that `CloseConnection` in `start_tls` takes effect immediately
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
            yield commands.Log(
                f"{self.debug}[quic] Swallowing {event} as handshake failed.", DEBUG
            )
