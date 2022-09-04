from __future__ import annotations
import asyncio
from dataclasses import dataclass, field
from ssl import VerifyMode
from typing import ClassVar, cast

from aioquic.buffer import Buffer as QuicBuffer
from aioquic.h3.connection import ErrorCode as H3ErrorCode
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
from aioquic.quic.packet import PACKET_TYPE_INITIAL, QuicProtocolVersion, encode_quic_version_negotiation, pull_quic_header
from cryptography import x509
from cryptography.hazmat.primitives.asymmetric import dsa, ec, rsa
from mitmproxy import certs, connection, ctx, flow as mitm_flow, log, tcp, udp
from mitmproxy.net import tls
from mitmproxy.net.udp import DatagramWriter
from mitmproxy.proxy import commands, context, events, layer, layers, mode_servers, server
from mitmproxy.proxy.utils import expect
from mitmproxy.tls import ClientHello, ClientHelloData, TlsData
from mitmproxy.utils import asyncio_utils, human


@dataclass
class QuicTlsSettings:
    """
    Settings necessary to establish QUIC's TLS context.
    """

    certificate: x509.Certificate | None = None
    """The certificate to use for the connection."""
    certificate_chain: list[x509.Certificate] = field(default_factory=list)
    """A list of additional certificates to send to the peer."""
    certificate_private_key: dsa.DSAPrivateKey | ec.EllipticCurvePrivateKey | rsa.RSAPrivateKey | None = (
        None
    )
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
    Event data for `quic_tls_start_client` and `quic_tls_start_server` event hooks.
    """

    settings: QuicTlsSettings | None = None
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
    """
    Connection-based event that is triggered whenever a new event from QUIC is received.

    Note:
    'Established' means that an OpenConnection command called in a child layer returned no error.
    Without a predefined child layer, the QUIC layer uses NextLayer mechanics to select the child
    layer. The moment is asks addons for the child layer, the connection is considered established.
    """

    event: quic_events.QuicEvent


class QuicStart(events.DataReceived):
    """
    Event that indicates that QUIC has been established on a given connection.
    This inherits from `DataReceived` in order to trigger next layer behavior and initialize HTTP clients.
    """

    quic: QuicConnection

    def __init__(self, connection: connection.Connection, quic: QuicConnection) -> None:
        super().__init__(connection, data=b"")
        self.quic = quic


class QuicTransmit(commands.ConnectionCommand):
    """Command that will transmit buffered data and re-arm the given QUIC connection's timer."""

    quic: QuicConnection

    def __init__(self, connection: connection.Connection, quic: QuicConnection) -> None:
        super().__init__(connection)
        self.quic = quic


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


@dataclass
class QuicClientHello(Exception):
    """Helper error only used in `pull_client_hello_and_connection_id`."""

    data: bytes


def pull_client_hello_and_connection_id(data: bytes) -> tuple[ClientHello, bytes]:
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


def build_configuration(conn: connection.Connection, settings: QuicTlsSettings) -> QuicConfiguration:
    """Creates a `QuicConfiguration` instance based on the given connection and TLS settings."""

    return QuicConfiguration(
        alpn_protocols=[offer.decode("ascii") for offer in conn.alpn_offers],
        connection_id_length=ctx.options.quic_connection_id_length,
        is_client=isinstance(conn, connection.Client),
        secrets_log_file=QuicSecretsLogger(tls.log_master_secret)  # type: ignore
        if tls.log_master_secret is not None
        else None,
        server_name=conn.sni,
        cafile=settings.ca_file,
        capath=settings.ca_path,
        certificate=settings.certificate,
        certificate_chain=settings.certificate_chain,
        cipher_suites=settings.cipher_suites,
        private_key=settings.certificate_private_key,
        verify_mode=settings.verify_mode,
    )


class QuicStream:
    flow: tcp.TCPFlow | None
    stream_id: int

    def __init__(self, context: context.Context, stream_id: int, ignore: bool) -> None:
        if ignore:
            self.flow = None
        else:
            self.flow = tcp.TCPFlow(context.client, context.server, live=True)
        self.stream_id = stream_id
        is_unidirectional = stream_is_unidirectional(stream_id)
        from_client = stream_is_client_initiated(stream_id)
        self._ended_client = is_unidirectional and not from_client
        self._ended_server = is_unidirectional and from_client

    def has_ended(self, client: bool) -> bool:
        return self._ended_client if client else self._ended_server

    def mark_ended(self, client: bool, err: str | None = None) -> layer.CommandGenerator[None]:
        # ensure we actually change the ended state
        if client:
            assert not self._ended_client
            self._ended_client = True
        else:
            assert not self._ended_server
            self._ended_server = True

        # we're done if the stream is ignored
        if self.flow is None:
            return

        # report any error if the flow hasn't one already
        if err is not None and self.flow.error is None:
            self.flow.error = mitm_flow.Error(str)
            yield layers.tcp.TcpErrorHook(self.flow)

        # report error-free endings and always clear the live flag
        if self._ended_client and self._ended_server:
            if self.flow.error is None:
                yield layers.tcp.TcpEndHook(self.flow)
            self.flow.live = False


class QuicStreamLayer(layer.Layer):
    """
    Layer on top of `ClientQuicLayer` and `ServerQuicLayer`, that simply relays all QUIC streams and datagrams.
    This layer is chosen by the default NextLayer addon if ALPN yields no known protocol.
    It uses `UDPFlow` and `TCPFlow` for datagrams and stream respectively, which makes message injection possible.
    """

    buffer_from_client: list[quic_events.QuicEvent]
    buffer_from_server: list[quic_events.QuicEvent]
    flow: udp.UDPFlow | None  # used for datagrams and to signal general connection issues
    quic_client: QuicConnection | None = None
    quic_server: QuicConnection | None = None
    streams_by_flow: dict[tcp.TCPFlow, QuicStream]
    streams_by_id: dict[int, QuicStream]

    def __init__(self, context: context.Context, ignore: bool = False) -> None:
        super().__init__(context)
        self.buffer_from_client = []
        self.buffer_from_server = []
        if ignore:
            self.flow = None
        else:
            self.flow = tcp.TCPFlow(self.context.client, self.context.server, live=True)
        self.streams_by_flow = {}
        self.streams_by_id = {}

    def get_or_create_stream(
        self, stream_id: int
    ) -> layer.CommandGenerator[QuicStream]:
        if stream_id in self.streams_by_id:
            return self.streams_by_id[stream_id]
        else:
            # register the stream and start the flow
            stream = QuicStream(self.context, stream_id, ignore=self.flow is None)
            self.streams_by_id[stream.stream_id] = stream
            if stream.flow is not None:
                self.streams_by_flow[stream.flow] = stream
                yield layers.tcp.TcpStartHook(stream.flow)
            return stream

    def handle_quic_event(
        self,
        event: quic_events.QuicEvent,
        from_client: bool,
    ) -> layer.CommandGenerator[None]:
        # buffer events if the peer is not ready yet
        peer_quic = self.quic_server if from_client else self.quic_client
        if peer_quic is None:
            (self.buffer_from_client if from_client else self.buffer_from_server).append(event)
            return
        peer_connection = self.context.server if from_client else self.context.client

        if isinstance(event, quic_events.DatagramFrameReceived):
            # forward datagrams (that are not stream-bound)
            if self.flow is not None:
                message = udp.UDPMessage(from_client, event.data)
                self.flow.messages.append(message)
                yield layers.udp.UdpMessageHook(self.flow)
                data = message.content
            else:
                data = event.data
            peer_quic.send_datagram_frame(data)

        elif isinstance(event, quic_events.StreamDataReceived):
            # ignore data received from already ended streams
            stream = yield from self.get_or_create_stream(event.stream_id)
            if stream.has_ended(from_client):
                yield commands.Log(f"Received {len(event.data)} byte(s) on already closed stream #{event.stream_id}.", level="debug")
                return

            # forward the message allowing addons to change it
            if stream.flow is not None:
                message = tcp.TCPMessage(from_client, event.data)
                stream.flow.messages.append(message)
                yield layers.tcp.TcpMessageHook(stream.flow)
                data = message.content
            else:
                data = event.data
            peer_quic.send_stream_data(
                stream.stream_id,
                data,
                event.end_stream,
            )

            # mark the stream as ended if needed
            if event.end_stream:
                yield from stream.mark_ended(from_client)

        elif isinstance(event, quic_events.StreamReset):
            # ignore resets from already ended streams
            stream = yield from self.get_or_create_stream(event.stream_id)
            if stream.has_ended(from_client):
                yield commands.Log(f"Received reset for already closed stream #{event.stream_id}.", level="debug")
                return

            # forward resets to peer streams and report them to addons
            peer_quic.reset_stream(
                stream.stream_id,
                event.error_code,
            )

            # mark the stream as failed
            yield from stream.mark_ended(from_client, err=error_code_to_str(event.error_code))

        else:
            # ignore other QUIC events
            yield commands.Log(f"Ignored QUIC event {event!r}.", level="debug")
            return

        # transmit data to the peer
        yield QuicTransmit(peer_connection, peer_quic)

    @expect(events.Start)
    def state_start(self, _) -> layer.CommandGenerator[None]:
        # mark the main flow as started
        if self.flow is not None:
            yield layers.udp.UdpStartHook(self.flow)

        # open the upstream connection if necessary
        if self.context.server.timestamp_start is None:
            err = yield commands.OpenConnection(self.context.server)
            if err:
                if self.flow is not None:
                    self.flow.error = mitm_flow.Error(str(err))
                    yield layers.udp.UdpErrorHook(self.flow)
                yield commands.CloseConnection(self.context.client)
                self._handle_event = self.state_done
                return
        self._handle_event = self.state_ready

    @expect(
        QuicStart,
        QuicConnectionEvent,
        layers.tcp.TcpMessageInjected,
        layers.udp.UdpMessageInjected,
        events.ConnectionClosed,
    )
    def state_ready(self, event: events.Event) -> layer.CommandGenerator[None]:

        if isinstance(event, events.ConnectionClosed):
            # define helper variables
            from_client = event.connection is self.context.client
            peer_conn = self.context.server if from_client else self.context.client
            peer_quic = self.quic_server if from_client else self.quic_client
            closed_quic = self.quic_client if from_client else self.quic_server
            close_event = None if closed_quic is None else closed_quic._close_event

            # close the peer as well (needs to be before hooks)
            if peer_quic is not None and close_event is not None:
                peer_quic.close(
                    close_event.error_code,
                    close_event.frame_type,
                    close_event.reason_phrase,
                )
                yield QuicTransmit(peer_conn, peer_quic)
            else:
                yield commands.CloseConnection(peer_conn)

            # report errors to the main flow
            if (
                self.flow is not None
                and close_event is not None
                and not is_success_error_code(close_event.error_code)
            ):
                self.flow.error = mitm_flow.Error(
                    close_event.reason_phrase
                    or error_code_to_str(close_event.error_code)
                )
                yield layers.udp.UdpErrorHook(self.flow)

            # we're done handling QUIC events, pass on to generic close handling
            self._handle_event = self.state_done
            yield from self.state_done(event)

        elif isinstance(event, QuicStart):
            # QUIC connection has been established, store it and get the peer's buffer
            from_client = event.connection is self.context.client
            buffer_from_peer = self.buffer_from_server if from_client else self.buffer_from_client
            if from_client:
                assert self.quic_client is None
                self.quic_client = event.quic
            else:
                assert self.quic_server is None
                self.quic_server = event.quic

            # flush the buffer to the other side
            for quic_event in buffer_from_peer:
                yield from self.handle_quic_event(quic_event, not from_client)
            buffer_from_peer.clear()

        elif isinstance(event, layers.tcp.TcpMessageInjected):
            # translate injected TCP messages into QUIC stream events
            assert isinstance(event.flow, tcp.TCPFlow)
            stream = self.streams_by_flow[event.flow]
            yield from self.handle_quic_event(
                quic_events.StreamDataReceived(
                    stream_id=stream.stream_id,
                    data=event.message.content,
                    end_stream=False,
                ),
                event.message.from_client,
            )

        elif isinstance(event, layers.udp.UdpMessageInjected):
            # translate injected UDP messages into QUIC datagram events
            assert isinstance(event.flow, udp.UDPFlow)
            assert event.flow is self.flow
            yield from self.handle_quic_event(
                quic_events.DatagramFrameReceived(data=event.message.content),
                event.message.from_client,
            )

        elif isinstance(event, QuicConnectionEvent):
            # handle or buffer QUIC events
            yield from self.handle_quic_event(
                event.event,
                from_client=event.connection is self.context.client,
            )

        else:
            raise AssertionError(f"Unexpected event: {event!r}")

    @expect(
        QuicStart,
        QuicConnectionEvent,
        layers.tcp.TcpMessageInjected,
        layers.udp.UdpMessageInjected,
        events.ConnectionClosed,
    )
    def state_done(self, event: events.Event) -> layer.CommandGenerator[None]:
        if isinstance(event, events.ConnectionClosed):
            from_client = event.connection is self.context.client

            # report the termination as error to all non-ended streams
            for stream in self.streams_by_id.values():
                if not stream.has_ended(from_client):
                    yield from stream.mark_ended(from_client, err="Connection closed.")

            # end the main flow
            if (
                self.flow is not None
                and not self.context.client.connected
                and not self.context.server.connected
            ):
                if self.flow.error is None:
                    yield layers.udp.UdpEndHook(self.flow)
                self.flow.live = False

    _handle_event = state_start


class QuicConnectionLayer(layer.Layer):
    child_layer: layer.Layer
    conn: connection.Connection
    original_destination_connection_id: bytes | None = None
    quic: QuicConnection | None = None
    tls: QuicTlsSettings | None = None

    writers: dict[connection.Address, DatagramWriter]
    """Writers of all known endpoints that send data to this instance."""

    def __init__(
        self,
        context: context.Context,
        conn: connection.Connection,
    ) -> None:
        super().__init__(context)
        self.child_layer = layer.NextLayer(context)
        self.conn = conn
        self._loop = asyncio.get_event_loop()
        self._pending_open_command: commands.OpenConnection | None = None
        self._pending_wakeup_commands: dict[commands.RequestWakeup, float] = dict()
        self._pending_data_received_events: list[events.DataReceived] = []
        self.conn.tls = True

    def build_configuration(self) -> QuicConfiguration:
        assert self.tls is not None

        return QuicConfiguration(
            alpn_protocols=[offer.decode("ascii") for offer in self.conn.alpn_offers],
            connection_id_length=self.context.options.quic_connection_id_length,
            is_client=self.conn is self.context.server,
            secrets_log_file=QuicSecretsLogger(tls.log_master_secret)  # type: ignore
            if tls.log_master_secret is not None
            else None,
            server_name=self.conn.sni,
            cafile=self.tls.ca_file,
            capath=self.tls.ca_path,
            certificate=self.tls.certificate,
            certificate_chain=self.tls.certificate_chain,
            cipher_suites=self.tls.cipher_suites,
            private_key=self.tls.certificate_private_key,
            verify_mode=self.tls.verify_mode,
        )

    def create_quic(self) -> layer.CommandGenerator[bool]:
        # must only be called if QUIC is uninitialized
        assert self.quic is None
        assert self.tls is None

        # cannot initialize QUIC on a closed connection
        if not self.conn.connected:
            return False

        # in case the connection is being reused, clear all handshake data
        self.conn.timestamp_tls_setup = None
        self.conn.certificate_list = ()
        self.conn.alpn = None
        self.conn.cipher = None
        self.conn.tls_version = None

        # query addons to provide the necessary TLS settings
        tls_data = QuicTlsData(self.conn, self.context)
        if self.conn is self.context.client:
            yield QuicTlsStartClientHook(tls_data)
        else:
            yield QuicTlsStartServerHook(tls_data)
        if tls_data.settings is None:
            yield commands.Log(
                f"{self.conn}: No QUIC TLS settings provided by addon(s).",
                level="error",
            )
            return False

        # create the aioquic connection
        self.tls = tls_data.settings
        self.quic = QuicConnection(
            configuration=self.build_configuration(),
            original_destination_connection_id=self.original_destination_connection_id,
        )
        self._handle_event = self.state_has_quic

        # issue the host connection ID right away
        self.issue_connection_id(self.quic.host_cid)

        # record an entry in the log
        yield commands.Log(f"{self.conn}: QUIC connection created.", level="info")
        return True

    def destroy_quic(
        self, event: quic_events.ConnectionTerminated
    ) -> layer.CommandGenerator[None]:
        # ensure QUIC has been properly shut down
        assert self.quic is not None
        assert self.tls is not None
        assert self.quic._state is QuicConnectionState.TERMINATED

        # report as TLS failure if the termination happened before the handshake
        reason = event.reason_phrase or error_code_to_str(event.error_code)
        if not self.conn.tls_established:
            self.conn.error = reason
            tls_data = QuicTlsData(self.conn, self.context, settings=self.tls)
            if self.conn is self.context.client:
                yield layers.tls.TlsFailedClientHook(tls_data)
            else:
                yield layers.tls.TlsFailedServerHook(tls_data)

        # clear the QUIC fields
        self.quic = None
        self.tls = None
        self._handle_event = self.state_no_quic

        # record an entry in the log
        yield commands.Log(
            f"{self.conn}: QUIC connection destroyed: {reason}",
            level="info" if is_success_error_code(event.error_code) else "warn",
        )

    def establish_quic(
        self, event: quic_events.HandshakeCompleted
    ) -> layer.CommandGenerator[None]:
        # must only be called if QUIC is initialized and not established
        assert self.quic is not None
        assert self.tls is not None
        assert not self.conn.tls_established

        # concatenate all peer certificates
        all_certs: list[x509.Certificate] = []
        if self.quic.tls._peer_certificate is not None:
            all_certs.append(self.quic.tls._peer_certificate)
        if self.quic.tls._peer_certificate_chain is not None:
            all_certs.extend(self.quic.tls._peer_certificate_chain)

        # set the connection's TLS properties
        self.conn.timestamp_tls_setup = self._loop.time()
        self.conn.certificate_list = [certs.Cert(cert) for cert in all_certs]
        self.conn.alpn = event.alpn_protocol.encode("ascii")
        self.conn.cipher = self.quic.tls.key_schedule.cipher_suite.name
        self.conn.tls_version = "QUIC"

        # report the success to addons
        tls_data = QuicTlsData(self.conn, self.context, settings=self.tls)
        if self.conn is self.context.client:
            yield layers.tls.TlsEstablishedClientHook(tls_data)
        else:
            yield layers.tls.TlsEstablishedServerHook(tls_data)

        # record an entry in the log
        yield commands.Log(
            f"{self.conn}: QUIC connection established. "
            f"(early_data={event.early_data_accepted}, resumed={event.session_resumed})",
            level="info",
        )

    def event_to_child(self, event: events.Event) -> layer.CommandGenerator[None]:
        # filter commands coming from the child layer
        for command in self.child_layer.handle_event(event):

            if isinstance(command, QuicTransmit) and command.connection is self.conn:
                # transmit buffered data and re-arm timer
                if command.quic is self.quic:
                    yield from self.transmit()

            elif (
                isinstance(command, commands.OpenConnection)
                and command.connection is self.conn
            ):
                # try to open the QUIC connection and report OpenConnectionCompleted later
                yield from self.open_connection_begin(command)

            elif (
                isinstance(command, commands.CloseConnection)
                and command.connection is self.conn
            ):
                # CloseConnection during pending OpenConnection is not allowed
                assert self._pending_open_command is None

                # without QUIC simply close the connection, otherwise close QUIC first
                if self.quic is None:
                    yield command
                else:
                    self.quic.close(reason_phrase="CloseConnection command received.")
                    yield from self.process_events()

            else:
                # return other commands
                yield command

    def issue_connection_id(self, connection_id: bytes) -> None:
        pass

    def open_connection_begin(
        self, command: commands.OpenConnection
    ) -> layer.CommandGenerator[None]:
        # ensure only one OpenConnection is called at a time and only for uninitialized connections
        assert self.quic is None
        assert self._pending_open_command is None
        self._pending_open_command = command

        # try to open the underlying UDP connection
        err = yield commands.OpenConnection(self.conn)
        if not err:
            # initialize QUIC and connect (notify the child layer after handshake)
            if (yield from self.create_quic()):
                assert self.quic is not None
                self.quic.connect(self.conn.peername, now=self._loop.time())
                yield from self.process_events()
            else:
                # TLS failed, close the connection (notify child layer once closed)
                yield commands.CloseConnection(self.conn)
        else:
            # notify the child layer immediately about the error
            self._pending_open_command = None
            yield from self.event_to_child(events.OpenConnectionCompleted(command, err))

    def open_connection_end(self, reply: str | None) -> layer.CommandGenerator[bool]:
        if self._pending_open_command is None:
            return False

        # let the child layer know that the connection is now open (or failed to open)
        command = self._pending_open_command
        self._pending_open_command = None
        yield from self.event_to_child(events.OpenConnectionCompleted(command, reply))
        return True

    def process_events(self) -> layer.CommandGenerator[None]:
        assert self.quic is not None

        # handle all buffered aioquic connection events
        event = self.quic.next_event()
        while event is not None:
            if isinstance(event, quic_events.ConnectionIdIssued):
                self.issue_connection_id(event.connection_id)

            elif isinstance(event, quic_events.ConnectionIdRetired):
                self.retire_connection_id(event.connection_id)

            elif isinstance(event, quic_events.ConnectionTerminated):
                # shutdown and close the connection
                yield from self.destroy_quic(event)
                yield commands.CloseConnection(self.conn)

                # we don't handle any further events, nor do/can we transmit data, so exit
                return

            elif isinstance(event, quic_events.HandshakeCompleted):
                # set all TLS fields and notify the child layer
                yield from self.establish_quic(event)
                yield from self.open_connection_end(None)
                yield from self.event_to_child(QuicStart(self.conn, self.quic))

            elif isinstance(event, quic_events.PingAcknowledged):
                # we let aioquic do it's thing but don't really care ourselves
                pass

            elif isinstance(event, quic_events.ProtocolNegotiated):
                # too early, we act on HandshakeCompleted
                pass

            elif isinstance(
                event,
                (
                    quic_events.DatagramFrameReceived,
                    quic_events.StreamDataReceived,
                    quic_events.StreamReset,
                ),
            ):
                # post-handshake event, forward as QuicConnectionEvent to the child layer
                assert self.conn.tls_established
                yield from self.event_to_child(QuicConnectionEvent(self.conn, event))

            else:
                raise AssertionError(f"Unexpected event: {event!r}")

            # handle the next event
            event = self.quic.next_event()

        # transmit buffered data and re-arm timer
        yield from self.transmit()

    def retire_connection_id(self, connection_id: bytes) -> None:
        pass

    def start(self) -> layer.CommandGenerator[None]:
        yield from self.event_to_child(events.Start())

    def state_after_quic(self, event: events.Event) -> layer.CommandGenerator[None]:
        assert self.quic is None

        if (
            isinstance(event, events.Wakeup)
            and event.command in self._pending_wakeup_commands
        ):
            # filter out obsolete wakeups
            del self._pending_wakeup_commands[event.command]

        else:
            # forward all other events to the child layer
            yield from self.event_to_child(event)

    def state_before_quic(self, event: events.Event) -> layer.CommandGenerator[None]:
        assert self.quic is None
        assert len(self._pending_wakeup_commands) == 0

        if (
            isinstance(event, events.ConnectionClosed) and event.connection is self.conn
        ):
            # if there was an OpenConnection command, then create_quic failed
            # otherwise the connection was opened before the QUIC layer, so forward the event
            if not (yield from self.open_connection_end("QUIC initialization failed")):
                yield from self.event_to_child(event)

        elif isinstance(event, events.DataReceived) and event.connection is self.conn:
            # buffer data until QUIC is initialized
            self._pending_data_received_events.append(event)

        else:
            # forward all other events to the child layer
            yield from self.event_to_child(event)

    def state_quic(self, event: events.Event) -> layer.CommandGenerator[None]:
        assert self.quic is not None

        if isinstance(event, events.DataReceived) and event.connection is self.conn:
            # forward incoming data only to aioquic
            assert event.remote_addr is not None
            self.quic.receive_datagram(
                event.data, event.remote_addr, now=self._loop.time()
            )
            yield from self.process_events()

        elif (
            isinstance(event, events.ConnectionClosed) and event.connection is self.conn
        ):
            # there is no point in calling quic.close, as it cannot send packets anymore
            # just set the new connection state and ensure there exists a close event
            self.quic._set_state(QuicConnectionState.TERMINATED)
            close_event = self.quic._close_event
            if close_event is None:
                close_event = quic_events.ConnectionTerminated(
                    error_code=QuicErrorCode.APPLICATION_ERROR,
                    frame_type=None,
                    reason_phrase="UDP connection closed or timed out.",
                )
                self.quic._close_event = close_event

            # shutdown QUIC and handle the ConnectionClosed event
            yield from self.destroy_quic(close_event)
            if not (
                yield from self.open_connection_end("QUIC could not be established")
            ):
                # connection was opened before QUIC layer, report to the child layer
                yield from self.event_to_child(event)

        elif isinstance(event, events.Wakeup):
            # handle issued wakeup commands and forward others to child layer
            if event.command in self._pending_wakeup_commands:
                self.quic.handle_timer(now=max(
                    self._pending_wakeup_commands.pop(event.command),
                    self._loop.time()
                ))
                yield from self.process_events()
            else:
                yield from self.event_to_child(event)

        else:
            # forward other events to the child layer
            yield from self.event_to_child(event)

    @expect(events.Start)
    def state_start(self, _) -> layer.CommandGenerator[None]:
        self._handle_event = self.state_before_quic
        yield from self.start()

    def transmit(self) -> layer.CommandGenerator[None]:
        assert self.quic is not None

        # send all queued datagrams
        for data, addr in self.quic.datagrams_to_send(now=self._loop.time()):
            yield commands.SendData(self.conn, data, addr)

        # request a new wakeup if all pending requests trigger at a later time
        timer = self.quic.get_timer()
        if not any(existing <= timer for existing in self._pending_wakeup_commands.values()):
            command = commands.RequestWakeup(timer - self._loop.time())
            self._pending_wakeup_commands[command] = timer
            yield command

    _handle_event = state_start


class ServerQuicLayer(_QuicLayer):
    """
    This layer establishes QUIC for a single server connection.
    """

    def __init__(
        self, context: context.Context, child_layer: layer.Layer | None = None
    ) -> None:
        super().__init__(context, context.server)
        if child_layer is not None:
            self.child_layer = child_layer


class QuicConnectionHandler(server.ConnectionHandler):
    """Handler for QUIC connections, required for roaming."""

    def __init__(self, context: context.Context, quic: QuicConnection) -> None:
        super().__init__(context)
        # TODO fork context and set different client conn
        handler = context.handler
        assert handler is not None
        self._handlers = {handler.client.peername: handler}

    def send_data(self, data: bytes, address: connection.Address) -> None:
        """Sends data via a different handler. The handler for the address needs to be registered."""
        handler = self._handlers[address]
        self.timeout_watchdog.register_activity()
        handler.timeout_watchdog.register_activity()
        handler.transports[handler.client].writer.write(data)

    def receive_data(self, data: bytes, address: connection.Address) -> None:
        """Receives data from another address. The address's peer handler need to be registered."""
        assert address in self._handlers
        self.client.peername = address
        self.server_event(events.DataReceived(self.client, data))

    def register_handler(self, handler: server.ConnectionHandler) -> None:
        """Registers a new peer handler."""
        assert self._handlers
        assert handler.client.address not in self._handlers
        self._handlers[handler.client.address] = handler

    def unregister_handler(self, handler: server.ConnectionHandler) -> None:
        """Removes the peer and shutdown the handler if it's the last one."""
        assert self._handlers[handler.client.address] == handler
        del self._handlers[handler.client.address]
        if not self._handlers:
            self.server_event(events.ConnectionClosed(self.client))
            del ClientQuicLayer.connections_by_client[self.client]

    async def handle_hook(self, hook: commands.StartHook) -> None:
        with self.timeout_watchdog.disarm():
            # keep in-sync with ProxyConnectionHandler
            (data,) = hook.args()
            await ctx.master.addons.handle_lifecycle(hook)
            if isinstance(data, mitm_flow.Flow):
                await data.wait_for_resume()  # pragma: no cover

    def log(self, message: str, level: str = "info") -> None:
        x = log.LogEntry(f"{human.format_address(self.client.address)}: {message}", level)
        asyncio_utils.create_task(
            ctx.master.addons.handle_lifecycle(log.AddLogHook(x)),
            name="QuicConnectionHandler.log",
        )


class ClientQuicLayer(layer.Layer):
    """Client-side layer performing routing and connection initialization."""

    connections_by_client: ClassVar[dict[connection.Client, QuicConnectionHandler]] = dict()
    """Mapping of client connections to quic connection handlers."""

    connections_by_id: ClassVar[dict[tuple[connection.Address, bytes], QuicConnectionHandler]] = dict()
    """Mapping of (sockname, cid) tuples to quic connection handlers."""

    def __init__(self, context: context.Context) -> None:
        if context.client.tls:
            # keep in sync with ClientTLSLayer
            context.client.alpn = None
            context.client.cipher = None
            context.client.sni = None
            context.client.timestamp_tls_setup = None
            context.client.tls_version = None
            context.client.certificate_list = []
            context.client.mitmcert = None
            context.client.alpn_offers = []
            context.client.cipher_list = []

        super().__init__(context)
        self._handlers: set[QuicConnectionHandler] = set()
        upper_layer = isinstance(self.context.layers[-2], ServerQuicLayer)
        self._server_quic_layer = upper_layer if isinstance(upper_layer, ServerQuicLayer) else None

    def datagram_received(self, event: events.DataReceived) -> layer.CommandGenerator[None]:
        # largely taken from aioquic's own asyncio server code and ClientTLSLayer
        buffer = QuicBuffer(data=event.data)
        try:
            header = pull_quic_header(
                buffer, host_cid_length=self.context.options.quic_connection_id_length
            )
        except ValueError:
            yield commands.Log("Invalid QUIC datagram received.")
            return

        # negotiate version, support all versions known to aioquic
        supported_versions = (
            version.value
            for version in QuicProtocolVersion
            if version is not QuicProtocolVersion.NEGOTIATION
        )
        if header.version is not None and header.version not in supported_versions:
            yield commands.SendData(
                event.connection,
                encode_quic_version_negotiation(
                    source_cid=header.destination_cid,
                    destination_cid=header.source_cid,
                    supported_versions=supported_versions,
                ),
            )
            return

        # get or create a handler for the connection
        connection_id = (header.destination_cid, self.context.client.sockname)
        handler = ClientQuicLayer.connections_by_id.get(connection_id, None)
        if handler is None:
            if len(event.data) < 1200 or header.packet_type != PACKET_TYPE_INITIAL:
                yield commands.Log(f"Invalid handshake received.")
                return

            # extract the client hello
            try:
                client_hello, connection_id = pull_client_hello_and_connection_id(
                    event.data
                )
            except ValueError as e:
                yield commands.Log(
                    f"Cannot parse ClientHello: {str(e)} ({event.data.hex()})"
                )
                return

            # copy the client hello information
            self.context.client.sni = client_hello.sni
            self.context.client.alpn_offers = client_hello.alpn_protocols

            # check with addons what we shall do
            hook_data = ClientHelloData(self.context, client_hello)
            yield layers.tls.TlsClienthelloHook(hook_data)

            # ignoring a connection is only allowed if there are no existing peers
            if hook_data.ignore_connection:
                assert not self._handlers

                # replace the QUIC layer with an UDP layer
                next_layer = layers.UDPLayer(self.context, ignore=True)
                prev_layer = (
                    self
                    if self._server_quic_layer is None else
                    self._server_quic_layer
                )
                prev_layer.handle_event = next_layer.handle_event
                prev_layer._handle_event = next_layer._handle_event
                yield from next_layer.handle_event(events.Start())
                yield from next_layer.handle_event(event)
                return

            # start the server QUIC connection if demanded and available
            if (
                hook_data.establish_server_tls_first
                and not self.context.server.tls_established
            ):
                err = (
                    yield commands.OpenConnection(self.context.server)
                    if self._server_quic_layer is not None else
                    "No server QUIC available."
                )
                if err:
                    yield commands.Log(
                        f"Unable to establish QUIC connection with server ({err}). "
                        f"Trying to establish QUIC with client anyway. "
                        f"If you plan to redirect requests away from this server, "
                        f"consider setting `connection_strategy` to `lazy` to suppress early connections."
                    )

            # query addons to provide the necessary TLS settings
            tls_data = QuicTlsData(self.context.client, self.context)
            yield QuicTlsStartClientHook(tls_data)
            if tls_data.settings is None:
                yield commands.Log("No client QUIC TLS settings provided by addon(s).", level="error")
                return

            # create and register the QUIC connection and handler
            handler = QuicConnectionHandler(
                context=self.context,
                quic=QuicConnection(
                    configuration=build_configuration(self.context.client, tls_data.settings),
                    original_destination_connection_id=header.destination_cid,
                )
            )
            ClientQuicLayer.connections_by_id[connection_id] = handler
            ClientQuicLayer.connections_by_client[handler.client] = handler

        else:
            # ensure that the handler is registered with the peer handler
            if handler not in self._handlers:
                handler.register_handler(self)
                self._handlers.add(handler)

        # forward the received packet
        handler.receive_data(event.data, self.context.client.peername)

    @expect(events.DataReceived, events.ConnectionClosed, events.MessageInjected)
    def state_route(self, event: events.Event) -> layer.CommandGenerator[None]:
        if isinstance(event, events.MessageInjected):
            # relay the injection based on the flow's client
            ClientQuicLayer.connections_by_client[event.flow.client_conn].server_event(event)

        elif isinstance(event, events.ConnectionClosed):
            assert event.connection is self.context.client
            # remove and unregister all peer handlers
            while self._handlers:
                self._handlers.pop().unregister_handler(self)

        elif isinstance(event, events.DataReceived):
            assert event.connection is self.context.client
            yield from self.datagram_received(event)

        else:
            raise AssertionError(f"Unexpected event: {event!r}")

    @expect(events.Start)
    def state_start(self, _) -> layer.CommandGenerator[None]:
        self._handle_event = self.state_route
        yield from ()

    _handle_event = state_start
