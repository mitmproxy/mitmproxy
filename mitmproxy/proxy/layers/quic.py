import asyncio
from dataclasses import dataclass, field
from ssl import VerifyMode
from typing import Callable, Dict, List, Literal, Optional, Set, Tuple, Union

from aioquic.buffer import Buffer as QuicBuffer
from aioquic.quic import events as quic_events
from aioquic.quic.configuration import QuicConfiguration
from aioquic.quic.connection import (
    QuicConnection,
    QuicConnectionError,
    QuicConnectionState,
    QuicErrorCode,
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
    event: quic_events.QuicEvent


class QuicGetConnection(commands.ConnectionCommand):  # -> Optional[QuicConnection]
    blocking = True


@dataclass(repr=False)
class QuicGetConnectionCompleted(events.CommandCompleted):
    command: QuicGetConnection
    reply: Optional[QuicConnection]


class QuicTransmit(commands.Command):
    connection: QuicConnection

    def __init__(self, connection: QuicConnection) -> None:
        super().__init__()
        self.connection = connection


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


class QuicRelayLayer(layer.Layer):
    # for now we're (ab)using the TCPFlow until https://github.com/mitmproxy/mitmproxy/pull/5414 is resolved
    datagram_flow: Optional[tcp.TCPFlow] = None
    lookup_server: Dict[int, Tuple[int, tcp.TCPFlow]]
    lookup_client: Dict[int, Tuple[int, tcp.TCPFlow]]
    quic_server: Optional[QuicConnection] = None
    quic_client: Optional[QuicConnection] = None

    def __init__(self, context: context.Context) -> None:
        super().__init__(context)
        self.lookup_server = {}
        self.lookup_client = {}

    def end_flow(
        self, flow: tcp.TCPFlow, event: quic_events.ConnectionTerminated
    ) -> layer.CommandGenerator[None]:
        if event.error_code == QuicErrorCode.NO_ERROR:
            yield tcp_layer.TcpEndHook(flow)
        else:
            flow.error = mitm_flow.Error(event.reason_phrase)
            yield tcp_layer.TcpErrorHook(flow)
        flow.live = False

    def get_quic(
        self, conn: connection.Connection
    ) -> layer.CommandGenerator[QuicConnection]:
        quic = yield QuicGetConnection(conn)
        assert isinstance(quic, QuicConnection)
        return quic

    def _handle_event(self, event: events.Event) -> layer.CommandGenerator[None]:
        if isinstance(event, events.Start):
            self.quic_server = yield from self.get_quic(self.context.server)
            self.quic_client = yield from self.get_quic(self.context.client)

        elif isinstance(event, QuicConnectionEvent):
            assert self.quic_server is not None
            assert self.quic_client is not None

            quic_event = event.event
            from_client = event.connection is self.context.client
            lookup_in = self.lookup_client if from_client else self.lookup_server
            lookup_out = self.lookup_server if from_client else self.lookup_client
            # quic_in = self.quic_client if from_client else self.quic_server
            quic_out = self.quic_server if from_client else self.quic_client

            # forward close and end all flows
            if isinstance(quic_event, quic_events.ConnectionTerminated):
                quic_out.close(
                    quic_event.error_code,
                    quic_event.frame_type,
                    quic_event.reason_phrase,
                )
                while lookup_in:
                    stream_id_in = next(iter(lookup_in))
                    stream_id_out, flow = lookup_in[stream_id_in]
                    yield from self.end_flow(flow, quic_event)
                    del lookup_in[stream_id_in]
                    del lookup_out[stream_id_out]

                if self.datagram_flow is not None:
                    yield from self.end_flow(flow, quic_event)
                    self.datagram_flow = None

            # forward datagrams (that are not stream-bound)
            elif isinstance(quic_event, quic_events.DatagramFrameReceived):
                if self.datagram_flow is None:
                    self.datagram_flow = tcp.TCPFlow(
                        self.context.client,
                        self.context.server,
                        live=True,
                    )
                    yield tcp_layer.TcpStartHook(self.datagram_flow)
                message = tcp.TCPMessage(from_client, quic_event.data)
                self.datagram_flow.messages.append(message)
                yield tcp_layer.TcpMessageHook(self.datagram_flow)
                quic_out.send_datagram_frame(message.content)

            # forward stream data
            elif isinstance(quic_event, quic_events.StreamDataReceived):
                # get or create the stream on the other side (and flow)
                stream_id_in = quic_event.stream_id
                if stream_id_in in lookup_in:
                    stream_id_out, flow = lookup_in[stream_id_in]
                else:
                    stream_id_out = quic_out.get_next_available_stream_id()
                    flow = tcp.TCPFlow(
                        self.context.client,
                        self.context.server,
                        live=True,
                    )
                    lookup_in[stream_id_in] = (stream_id_out, flow)
                    lookup_out[stream_id_out] = (stream_id_in, flow)
                    yield tcp_layer.TcpStartHook(flow)

                # forward the message allowing addons to change it
                message = tcp.TCPMessage(from_client, quic_event.data)
                flow.messages.append(message)
                yield tcp_layer.TcpMessageHook(flow)
                quic_out.send_stream_data(
                    stream_id_out,
                    message.content,
                    quic_event.end_stream,
                )

                # end the flow and remove the lookup if the stream ended
                if quic_event.end_stream:
                    yield tcp_layer.TcpEndHook(flow)
                    flow.live = False
                    del lookup_in[stream_id_in]
                    del lookup_out[stream_id_out]

            # forward resets to peer streams
            elif isinstance(quic_event, quic_events.StreamReset):
                stream_id_in = quic_event.stream_id
                if stream_id_in in lookup_in:
                    stream_id_out, flow = lookup_in[stream_id_in]
                    quic_out.stop_stream(stream_id_out, quic_event.error_code)

                    # try to get a name describing the reset reason
                    try:
                        err = QuicErrorCode(quic_event.error_code).name
                    except ValueError:
                        err = str(quic_event.error_code)

                    # report the error to addons and delete the stream
                    flow.error = mitm_flow.Error(str(err))
                    yield tcp_layer.TcpErrorHook(flow)
                    flow.live = False
                    del lookup_in[stream_id_in]
                    del lookup_out[stream_id_out]


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

        # clear the quic fields
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
        all_certs = []
        if self.quic.tls._peer_certificate is not None:
            all_certs.append(self.quic.tls._peer_certificate)
        if self.quic.tls._peer_certificate_chain is not None:
            all_certs.extend(self.quic.tls._peer_certificate_chain)

        # set the connection's TLS properties
        self.conn.timestamp_tls_setup = self._loop.time()
        self.conn.certificate_list = [certs.Cert.from_pyopenssl(x) for x in all_certs]
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
        yield from self.handle_child_commands(self.child_layer.handle_event(event))

    def handle_child_commands(
        self, child_commands: layer.CommandGenerator[None]
    ) -> layer.CommandGenerator[None]:
        # filter commands coming from the child layer
        for command in child_commands:

            # answer with the aioquic connection instance
            if (
                isinstance(command, QuicGetConnection)
                and command.connection is self.conn
            ):
                yield from self.event_to_child(
                    QuicGetConnectionCompleted(command, self.quic)
                )

            # transmit buffered data and re-arm timer
            elif isinstance(command, QuicTransmit) and command.connection is self.quic:
                yield from self.transmit()

            # open the QUIC connection
            elif (
                isinstance(command, commands.OpenConnection)
                and command.connection is self.conn
            ):
                yield from self.open_connection_begin(command)

            # properly close QUIC connections
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

            # return other commands
            else:
                yield command

    def open_connection_begin(
        self, command: commands.OpenConnection
    ) -> layer.CommandGenerator[None]:
        # ensure only one OpenConnection at a time is called for uninitialized connections
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
                # only forward the event if the connection has been properly initialized
                if self.conn.tls_established:
                    yield from self.event_to_child(
                        QuicConnectionEvent(self.conn, event)
                    )

                # shutdown and close the connection
                yield from self.destroy_quic(
                    event.reason_phrase or str(event.error_code),
                    level=(
                        "info" if event.error_code == QuicErrorCode.NO_ERROR else "warn"
                    ),
                )
                yield commands.CloseConnection(self.conn)

                # we don't handle any further events, nor do/can we transmit data, so exit
                return

            elif isinstance(event, quic_events.HandshakeCompleted):
                # set all TLS fields and notify the child layer
                yield from self.establish_quic(event)
                yield from self.open_connection_end(None)

                # perform next layer decisions now
                if isinstance(self.child_layer, layer.NextLayer):
                    yield from self.handle_child_commands(self.child_layer._ask())

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
                raise AssertionError(f"Unexpected event: {event}")

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
            # handle connections closed by peer, which in UDP's case is a timeout
            reason = "Peer UDP connection timed out."

            # there is no point in calling quic.close, as it cannot send packets anymore
            # set the new connection state and simulate a ConnectionTerminated event (if established)
            self.quic._set_state(QuicConnectionState.TERMINATED)
            if self.conn.tls_established:
                yield from self.event_to_child(
                    QuicConnectionEvent(
                        self.conn,
                        quic_events.ConnectionTerminated(
                            error_code=QuicErrorCode.APPLICATION_ERROR,
                            frame_type=None,
                            reason_phrase=reason,
                        ),
                    )
                )

            # shutdown QUIC and handle the ConnectionClosed event
            yield from self.destroy_quic(reason, level="info")
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
            # if there is was an OpenConnection command, then create_quic failed
            # otherwise the connection was opened before the QUIC layer, so forward the event
            if not (yield from self.open_connection_end("QUIC initialization failed")):
                yield from self.event_to_child(event)

        elif isinstance(event, events.DataReceived) and event.connection is self.conn:
            # ignore received data events
            # this either happens after QUIC is closed or if the underlying UDP connection is opened
            # before the QUIC layer and missing initialization during the child layer's start event
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

        # mark an existing wakeup command as obsolete if it now longer matches the time
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

    def __init__(self, context: context.Context) -> None:
        super().__init__(context, context.server)


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

        # if (still) connected then initialize, close on failure
        if self.conn.connected and not (yield from self.create_quic()):
            yield commands.CloseConnection(self.conn)
            if self.wait_for_upstream and err is not None:
                yield commands.CloseConnection(self.context.server)
            self._handle_event = self.state_failed

    @expect(events.ConnectionClosed, events.DataReceived, QuicConnectionEvent)
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
                self.handle_event = next_layer.handle_event
                self._handle_event = next_layer._handle_event
                yield from next_layer.handle_event(events.Start())
                yield from next_layer.handle_event(event)

        # stop if the connection was closed (usually we will always get one packet)
        elif isinstance(event, events.ConnectionClosed):
            self._handle_event = self.state_done

        else:
            raise AssertionError(f"Unexpected event: {event}")

    _handle_event = state_start
