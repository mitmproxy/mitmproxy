import asyncio
from dataclasses import dataclass, field
from ssl import VerifyMode
from typing import Callable, Dict, List, Literal, Optional, Set, Tuple, Union

from aioquic.buffer import Buffer as QuicBuffer
from aioquic.h3.connection import ErrorCode as H3ErrorCode
from aioquic.quic import events as quic_events
from aioquic.quic.configuration import QuicConfiguration
from aioquic.quic.connection import (
    QuicConnection,
    QuicConnectionError,
    QuicConnectionState,
    QuicErrorCode,
    stream_is_unidirectional,
)
from aioquic.tls import CipherSuite, HandshakeType
from aioquic.quic.packet import PACKET_TYPE_INITIAL, pull_quic_header
from cryptography import x509
from cryptography.hazmat.primitives.asymmetric import dsa, ec, rsa
from mitmproxy import certs, connection, flow as mitm_flow, tcp
from mitmproxy.net import tls
from mitmproxy.proxy import commands, context, events, layer, layers
from mitmproxy.proxy.layers import tcp as tcp_layer
from mitmproxy.proxy.utils import expect
from mitmproxy.tls import ClientHello, ClientHelloData, TlsData


@dataclass
class QuicTlsSettings:
    """
    Settings necessary to establish QUIC's TLS context.
    """

    certificate: Optional[x509.Certificate] = None
    """The certificate to use for the connection."""
    certificate_chain: List[x509.Certificate] = field(default_factory=list)
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


def pull_client_hello_and_connection_id(data: bytes) -> Tuple[ClientHello, bytes]:
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


@dataclass
class QuicRelayStream:
    client_ended: bool
    client_id: int
    flow: tcp.TCPFlow
    server_ended: bool
    server_id: int

    def stream_id(self, client: bool) -> int:
        return self.client_id if client else self.server_id

    def has_ended(self, client: bool) -> bool:
        stream_ended = self.client_ended if client else self.server_ended
        return stream_ended or not self.flow.live


class QuicRelayLayer(layer.Layer):
    """
    Layer on top of `ClientQuicLayer` and `ServerQuicLayer`, that simply relays all QUIC streams and datagrams.
    This layer is chosen by the default NextLayer addon if ALPN yields no known protocol.
    """

    # NOTE: for now we're (ab)using the TCPFlow until https://github.com/mitmproxy/mitmproxy/pull/5414 is resolved

    buffer_from_client: List[quic_events.QuicEvent]
    buffer_from_server: List[quic_events.QuicEvent]
    flow: tcp.TCPFlow  # used for datagrams and to signal general connection issues
    quic_client: Optional[QuicConnection] = None
    quic_server: Optional[QuicConnection] = None
    streams_by_flow: Dict[tcp.TCPFlow, QuicRelayStream]
    streams_by_client_id: Dict[int, QuicRelayStream]
    streams_by_server_id: Dict[int, QuicRelayStream]

    def __init__(self, context: context.Context) -> None:
        super().__init__(context)
        self.buffer_from_client = []
        self.buffer_from_server = []
        self.flow = tcp.TCPFlow(
            self.context.client,
            self.context.server,
            live=True,
        )
        self.streams_by_flow = {}
        self.streams_by_client_id = {}
        self.streams_by_server_id = {}

    def get_or_create_stream(
        self, stream_id: int, from_client: bool
    ) -> layer.CommandGenerator[QuicRelayStream]:
        streams_by_id = (
            self.streams_by_client_id if from_client else self.streams_by_server_id
        )
        if stream_id in streams_by_id:
            return streams_by_id[stream_id]
        else:
            # reserve the peer stream id
            is_unidirectional = stream_is_unidirectional(stream_id)
            peer_quic = self.quic_server if from_client else self.quic_client
            assert peer_quic
            peer_stream_id = peer_quic.get_next_available_stream_id(is_unidirectional)

            # create the instance and make sure unidirectional streams are marked as ended
            stream = QuicRelayStream(
                flow=tcp.TCPFlow(
                    self.context.client,
                    self.context.server,
                    live=True,
                ),
                client_ended=is_unidirectional and not from_client,
                server_ended=is_unidirectional and from_client,
                client_id=stream_id if from_client else peer_stream_id,
                server_id=peer_stream_id if from_client else stream_id,
            )

            # register the stream and start the flow
            self.streams_by_flow[stream.flow] = stream
            self.streams_by_client_id[stream.client_id] = stream
            self.streams_by_server_id[stream.server_id] = stream
            yield tcp_layer.TcpStartHook(stream.flow)
            return stream

    def handle_quic_event(
        self,
        event: quic_events.QuicEvent,
        from_client: bool,
        allow_buffering: bool,
    ) -> layer.CommandGenerator[None]:
        # buffer events if the peer is not ready yet
        peer_quic = self.quic_server if from_client else self.quic_client
        if peer_quic is None:
            if not allow_buffering:
                raise AssertionError(
                    f"Cannot buffer event from {'client' if from_client else 'server'}."
                )
            if from_client:
                self.buffer_from_client.append(event)
            else:
                self.buffer_from_server.append(event)
            return
        peer_connection = self.context.server if from_client else self.context.client

        if isinstance(event, quic_events.DatagramFrameReceived):
            # forward datagrams (that are not stream-bound)
            if not self.flow.live:
                return
            message = tcp.TCPMessage(from_client, event.data)
            self.flow.messages.append(message)
            yield tcp_layer.TcpMessageHook(self.flow)
            peer_quic.send_datagram_frame(message.content)

        elif isinstance(event, quic_events.StreamDataReceived):
            # ignore data received from already ended streams
            stream = yield from self.get_or_create_stream(event.stream_id, from_client)
            if stream.has_ended(from_client):
                return

            # forward the message allowing addons to change it
            message = tcp.TCPMessage(from_client, event.data)
            stream.flow.messages.append(message)
            yield tcp_layer.TcpMessageHook(stream.flow)
            peer_quic.send_stream_data(
                stream_id=stream.stream_id(not from_client),
                data=message.content,
                end_stream=event.end_stream,
            )

            # mark the stream as ended if needed
            if event.end_stream:
                if from_client:
                    stream.client_ended = True
                else:
                    stream.server_ended = True

                # end the flow if both legs ended
                if stream.client_ended and stream.server_ended:
                    yield tcp_layer.TcpEndHook(stream.flow)
                    stream.flow.live = False

        elif isinstance(event, quic_events.StreamReset):
            # ignore resets from already ended streams
            stream = yield from self.get_or_create_stream(event.stream_id, from_client)
            if stream.has_ended(from_client):
                return

            # forward resets to peer streams and report them to addons
            peer_quic.reset_stream(
                stream_id=stream.stream_id(not from_client),
                error_code=event.error_code,
            )
            stream.flow.error = mitm_flow.Error(error_code_to_str(event.error_code))
            yield tcp_layer.TcpErrorHook(stream.flow)
            stream.flow.live = False

        else:
            # ignore other QUIC events
            return

        # transmit data to the peer
        yield QuicTransmit(peer_connection, peer_quic)

    @expect(events.Start)
    def state_start(self, _) -> layer.CommandGenerator[None]:
        # mark the main flow as started
        yield tcp_layer.TcpStartHook(self.flow)

        # open the upstream connection if necessary
        if self.context.server.timestamp_start is None:
            err = yield commands.OpenConnection(self.context.server)
            if err:
                self.flow.error = mitm_flow.Error(str(err))
                yield tcp_layer.TcpErrorHook(self.flow)
                self.flow.live = False
                yield commands.CloseConnection(self.context.client)
                self._handle_event = self.state_done
                return
        self._handle_event = self.state_ready

    @expect(
        QuicStart,
        QuicConnectionEvent,
        tcp_layer.TcpMessageInjected,
        events.ConnectionClosed,
    )
    def state_ready(self, event: events.Event) -> layer.CommandGenerator[None]:

        if isinstance(event, events.ConnectionClosed):
            # define helper variables
            from_client = event.connection is self.context.client
            peer_conn = self.context.server if from_client else self.context.client
            local_quic = self.quic_client if from_client else self.quic_server
            peer_quic = self.quic_server if from_client else self.quic_client
            assert local_quic is not None
            close_event = local_quic._close_event
            assert close_event is not None

            # report the termination as error to all non-ended streams
            for flow in self.streams_by_flow:
                if flow.live:
                    self.flow.error = mitm_flow.Error("Connection closed.")
                    yield tcp_layer.TcpErrorHook(flow)
                    flow.live = False

            # end the main flow
            if self.flow.live:
                if is_success_error_code(close_event.error_code):
                    yield tcp_layer.TcpEndHook(flow)
                else:
                    self.flow.error = mitm_flow.Error(
                        close_event.reason_phrase
                        or error_code_to_str(close_event.error_code)
                    )
                    yield tcp_layer.TcpErrorHook(flow)
                self.flow.live = False

            # close the peer as well
            if peer_quic is not None:
                peer_quic.close(
                    close_event.error_code,
                    close_event.frame_type,
                    close_event.reason_phrase,
                )
                yield QuicTransmit(peer_conn, peer_quic)
            else:
                yield commands.CloseConnection(peer_conn)
            self._handle_event = self.state_done

        elif isinstance(event, QuicStart):
            # QUIC connection has been established, store it and flush buffered events
            if event.connection is self.context.client:
                assert self.quic_client is None
                self.quic_client = event.quic
                for quic_event in self.buffer_from_server:
                    yield from self.handle_quic_event(
                        quic_event,
                        from_client=False,
                        allow_buffering=False,
                    )
            elif event.connection is self.context.server:
                assert self.quic_server is None
                self.quic_server = event.quic
                for quic_event in self.buffer_from_client:
                    yield from self.handle_quic_event(
                        quic_event,
                        from_client=True,
                        allow_buffering=False,
                    )
            else:
                raise AssertionError(
                    f"Connection {event.connection} not associated with layer."
                )

        elif isinstance(event, tcp_layer.TcpMessageInjected):
            # translate injected messages into QUIC events
            assert isinstance(event.flow, tcp.TCPFlow)
            if event.flow is self.flow:
                yield from self.handle_quic_event(
                    quic_events.DatagramFrameReceived(event.message.content),
                    event.message.from_client,
                    allow_buffering=True,
                )
            elif event.flow in self.streams_by_flow:
                stream = self.streams_by_flow[event.flow]
                yield from self.handle_quic_event(
                    quic_events.StreamDataReceived(
                        stream_id=(
                            stream.client_id
                            if event.message.from_client
                            else stream.server_id
                        ),
                        data=event.message.content,
                        end_stream=False,
                    ),
                    event.message.from_client,
                    allow_buffering=True,
                )
            else:
                raise AssertionError(
                    f"Flow {event.flow} not associated with the current layer."
                )

        elif isinstance(event, QuicConnectionEvent):
            # handle or buffer QUIC events
            yield from self.handle_quic_event(
                event.event,
                from_client=event.connection is self.context.client,
                allow_buffering=True,
            )

        else:
            raise AssertionError(f"Unexpected event: {event!r}")

    @expect(
        QuicStart,
        QuicConnectionEvent,
        tcp_layer.TcpMessageInjected,
        events.ConnectionClosed,
    )
    def state_done(self, _) -> layer.CommandGenerator[None]:
        yield from ()

    _handle_event = state_start


class _QuicLayer(layer.Layer):
    child_layer: layer.Layer
    conn: connection.Connection
    issue_connection_id_callback: Optional[Callable[[bytes], None]] = None
    original_destination_connection_id: Optional[bytes] = None
    quic: Optional[QuicConnection] = None
    retire_connection_id_callback: Optional[Callable[[bytes], None]] = None
    tls: Optional[QuicTlsSettings] = None

    def __init__(
        self,
        context: context.Context,
        conn: connection.Connection,
    ) -> None:
        super().__init__(context)
        self.child_layer = layer.NextLayer(context)
        self.conn = conn
        self._loop = asyncio.get_event_loop()
        self._pending_open_command: Optional[commands.OpenConnection] = None
        self._request_wakeup_command_and_timer: Optional[
            Tuple[commands.RequestWakeup, float]
        ] = None
        self._obsolete_wakeup_commands: Set[commands.RequestWakeup] = set()
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
        if self.issue_connection_id_callback is not None:
            self.issue_connection_id_callback(self.quic.host_cid)

        # record an entry in the log
        yield commands.Log(f"{self.conn}: QUIC connection created.", level="info")
        return True

    def destroy_quic(
        self,
        reason: str,
        level: Literal["error", "warn", "info", "alert", "debug"],
    ) -> layer.CommandGenerator[None]:
        # ensure QUIC has been properly shut down
        assert self.quic is not None
        assert self.tls is not None
        assert self.quic._state is QuicConnectionState.TERMINATED

        # report as TLS failure if the termination happened before the handshake
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

        # obsolete any current timer
        if self._request_wakeup_command_and_timer is not None:
            command, _ = self._request_wakeup_command_and_timer
            self._obsolete_wakeup_commands.add(command)
            self._request_wakeup_command_and_timer = None

        # record an entry in the log
        yield commands.Log(
            f"{self.conn}: QUIC connection destroyed: {reason}", level=level
        )

    def establish_quic(
        self, event: quic_events.HandshakeCompleted
    ) -> layer.CommandGenerator[None]:
        # must only be called if QUIC is initialized
        assert self.quic is not None
        assert self.tls is not None

        # concatenate all peer certificates
        all_certs: List[x509.Certificate] = []
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

    def open_connection_end(self, reply: Optional[str]) -> layer.CommandGenerator[bool]:
        if self._pending_open_command is None:
            return False

        # let the child layer know that the connection is now open (or failed to open)
        command = self._pending_open_command
        self._pending_open_command = None
        yield from self.event_to_child(events.OpenConnectionCompleted(command, reply))
        return True

    def process_events(self) -> layer.CommandGenerator[None]:
        assert self.quic is not None
        assert self.tls is not None

        # handle all buffered aioquic connection events
        event = self.quic.next_event()
        while event is not None:
            if isinstance(event, quic_events.ConnectionIdIssued):
                if self.issue_connection_id_callback is not None:
                    self.issue_connection_id_callback(event.connection_id)

            elif isinstance(event, quic_events.ConnectionIdRetired):
                if self.retire_connection_id_callback is not None:
                    self.retire_connection_id_callback(event.connection_id)

            elif isinstance(event, quic_events.ConnectionTerminated):
                # shutdown and close the connection
                yield from self.destroy_quic(
                    event.reason_phrase or error_code_to_str(event.error_code),
                    level=(
                        "info" if is_success_error_code(event.error_code) else "warn"
                    ),
                )
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

    def start(self) -> layer.CommandGenerator[None]:
        yield from self.event_to_child(events.Start())

    def state_has_quic(self, event: events.Event) -> layer.CommandGenerator[None]:
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
            # just set the new connection state and ensure there is exists a close event
            self.quic._set_state(QuicConnectionState.TERMINATED)
            if self.quic._close_event is None:
                self.quic._close_event = quic_events.ConnectionTerminated(
                    error_code=QuicErrorCode.APPLICATION_ERROR,
                    frame_type=None,
                    reason_phrase="Peer UDP connection closed or timed out.",
                )

            # shutdown QUIC and handle the ConnectionClosed event
            reason = self.quic._close_event.reason_phrase or error_code_to_str(
                self.quic._close_event.error_code
            )
            yield from self.destroy_quic(
                reason,
                level="info",
            )
            if not (yield from self.open_connection_end(reason)):
                # connection was opened before QUIC layer, report to the child layer
                yield from self.event_to_child(event)

        elif isinstance(event, events.Wakeup):
            # swallow obsolete wakeup events
            if event.command in self._obsolete_wakeup_commands:
                self._obsolete_wakeup_commands.remove(event.command)
            else:
                # handle active wakeup and forward others to child layer
                if self._request_wakeup_command_and_timer is not None:
                    command, timer = self._request_wakeup_command_and_timer
                    if event.command is command:
                        self._request_wakeup_command_and_timer = None
                        self.quic.handle_timer(now=max(timer, self._loop.time()))
                        yield from self.process_events()
                    else:
                        yield from self.event_to_child(event)
                else:
                    yield from self.event_to_child(event)

        else:
            # forward other events to the child layer
            yield from self.event_to_child(event)

    def state_no_quic(self, event: events.Event) -> layer.CommandGenerator[None]:
        assert self.quic is None

        if (
            isinstance(event, events.Wakeup)
            and event.command in self._obsolete_wakeup_commands
        ):
            # filter out obsolete wakeups
            self._obsolete_wakeup_commands.remove(event.command)

        elif (
            isinstance(event, events.ConnectionClosed) and event.connection is self.conn
        ):
            # if there was an OpenConnection command, then create_quic failed
            # otherwise the connection was opened before the QUIC layer, so forward the event
            if not (yield from self.open_connection_end("QUIC initialization failed")):
                yield from self.event_to_child(event)

        elif isinstance(event, events.DataReceived) and event.connection is self.conn:
            # ignore received data, which either happens after QUIC is closed or if the underlying
            # UDP connection is already opened and no QUIC initialization is being performed
            pass

        else:
            # forward all other events to the child layer
            yield from self.event_to_child(event)

    @expect(events.Start)
    def state_start(self, _) -> layer.CommandGenerator[None]:
        self._handle_event = self.state_no_quic
        yield from self.start()

    def transmit(self) -> layer.CommandGenerator[None]:
        assert self.quic is not None

        # send all queued datagrams
        for data, addr in self.quic.datagrams_to_send(now=self._loop.time()):
            yield commands.SendData(self.conn, data, addr)

        # mark an existing wakeup command as obsolete if it no longer matches the timer
        timer = self.quic.get_timer()
        if self._request_wakeup_command_and_timer is not None:
            command, existing_timer = self._request_wakeup_command_and_timer
            if existing_timer != timer:
                self._obsolete_wakeup_commands.add(command)
                self._request_wakeup_command_and_timer = None

        # request a new wakeup if necessary
        if timer is not None and self._request_wakeup_command_and_timer is None:
            command = commands.RequestWakeup(timer - self._loop.time())
            self._request_wakeup_command_and_timer = (command, timer)
            yield command

    _handle_event = state_start


class ServerQuicLayer(_QuicLayer):
    """
    This layer establishes QUIC for a single server connection.
    """

    def __init__(
        self, context: context.Context, child_layer: Optional[layer.Layer] = None
    ) -> None:
        super().__init__(context, context.server)
        if child_layer is not None:
            self.child_layer = child_layer


class ClientQuicLayer(_QuicLayer):
    """
    This layer establishes QUIC on a single client connection.
    """

    wait_for_upstream: bool

    def __init__(
        self,
        context: context.Context,
        wait_for_upstream: bool,
    ) -> None:
        super().__init__(context, context.client)
        self.wait_for_upstream = wait_for_upstream

    def start(self) -> layer.CommandGenerator[None]:
        yield from super().start()

        # try to open the upstream connection
        if self.wait_for_upstream:
            err = yield commands.OpenConnection(self.context.server)
            if err:
                yield commands.Log(
                    f"Unable to establish QUIC connection with server ({err}). "
                    f"Trying to establish QUIC with client anyway."
                )

        # initialize QUIC, shutdown on failure
        if not (yield from self.create_quic()):
            yield commands.CloseConnection(self.conn)
            if self.wait_for_upstream and err is not None:
                yield commands.CloseConnection(self.context.server)
            self._handle_event = self.state_failed

    def state_failed(self, _) -> layer.CommandGenerator[None]:
        yield from ()


class QuicLayer(layer.Layer):
    """
    Entry layer for QUIC proxy server.
    """

    def __init__(
        self,
        context: context.Context,
        issue_cid: Callable[[bytes], None],
        retire_cid: Callable[[bytes], None],
    ) -> None:
        super().__init__(context)
        self._issue_cid = issue_cid
        self._retire_cid = retire_cid
        self.context.client.tls = True
        self.context.server.tls = True

    def build_client_layer(
        self, connection_id: bytes, wait_for_upstream: bool
    ) -> ClientQuicLayer:
        layer = ClientQuicLayer(self.context, wait_for_upstream)
        layer.original_destination_connection_id = connection_id
        layer.issue_connection_id_callback = self._issue_cid
        layer.retire_connection_id_callback = self._retire_cid
        return layer

    @expect(events.DataReceived, events.ConnectionClosed)
    def state_done(self, _) -> layer.CommandGenerator[None]:
        yield from ()

    @expect(events.Start)
    def state_start(self, _) -> layer.CommandGenerator[None]:
        self._handle_event = self.state_wait_for_hello
        yield from ()

    @expect(events.DataReceived, events.ConnectionClosed)
    def state_wait_for_hello(self, event: events.Event) -> layer.CommandGenerator[None]:
        assert isinstance(event, events.ConnectionEvent)
        assert event.connection is self.context.client

        # only handle the first packet from the client
        if isinstance(event, events.DataReceived):
            # extract the client hello
            try:
                client_hello, connection_id = pull_client_hello_and_connection_id(
                    event.data
                )
            except ValueError as e:
                yield commands.Log(
                    f"Cannot parse ClientHello: {str(e)} ({event.data.hex()})"
                )
                yield commands.CloseConnection(self.context.client)
                self._handle_event = self.state_done
            else:

                # copy the information
                self.context.client.sni = client_hello.sni
                self.context.client.alpn_offers = client_hello.alpn_protocols

                # check with addons what we shall do
                next_layer: layer.Layer
                hook_data = ClientHelloData(self.context, client_hello)
                yield layers.tls.TlsClienthelloHook(hook_data)

                # simply relay everything
                if hook_data.ignore_connection:
                    next_layer = layers.TCPLayer(self.context, ignore=True)

                # contact the upstream server first
                elif hook_data.establish_server_tls_first:
                    next_layer = ServerQuicLayer(self.context)
                    next_layer.child_layer = self.build_client_layer(
                        connection_id,
                        wait_for_upstream=True,
                    )

                # perform the client handshake immediately
                else:
                    next_layer = self.build_client_layer(
                        connection_id,
                        wait_for_upstream=False,
                    )

                # replace this layer and start the next one
                self.handle_event = next_layer.handle_event  # type: ignore
                self._handle_event = next_layer._handle_event
                yield from next_layer.handle_event(events.Start())
                yield from next_layer.handle_event(event)

        # stop if the connection was closed (usually we will always get one packet)
        elif isinstance(event, events.ConnectionClosed):
            self._handle_event = self.state_done

        else:
            raise AssertionError(f"Unexpected event: {event!r}")

    _handle_event = state_start
