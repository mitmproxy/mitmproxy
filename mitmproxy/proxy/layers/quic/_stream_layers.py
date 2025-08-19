"""
This module contains the client and server proxy layers for QUIC streams
which decrypt and encrypt traffic. Decrypted stream data is then forwarded
to either the raw layers, or the HTTP/3 client in ../http/_http3.py.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from logging import DEBUG
from logging import ERROR
from logging import WARNING

from aioquic.buffer import Buffer as QuicBuffer
from aioquic.h3.connection import ErrorCode as H3ErrorCode
from aioquic.quic import events as quic_events
from aioquic.quic.configuration import QuicConfiguration
from aioquic.quic.connection import QuicConnection
from aioquic.quic.connection import QuicConnectionState
from aioquic.quic.connection import QuicErrorCode
from aioquic.quic.packet import encode_quic_version_negotiation
from aioquic.quic.packet import PACKET_TYPE_INITIAL
from aioquic.quic.packet import pull_quic_header
from cryptography import x509

from ._client_hello_parser import quic_parse_client_hello_from_datagrams
from ._commands import CloseQuicConnection
from ._commands import QuicStreamCommand
from ._commands import ResetQuicStream
from ._commands import SendQuicStreamData
from ._commands import StopSendingQuicStream
from ._events import QuicConnectionClosed
from ._events import QuicStreamDataReceived
from ._events import QuicStreamReset
from ._events import QuicStreamStopSending
from ._hooks import QuicStartClientHook
from ._hooks import QuicStartServerHook
from ._hooks import QuicTlsData
from ._hooks import QuicTlsSettings
from mitmproxy import certs
from mitmproxy import connection
from mitmproxy import ctx
from mitmproxy.net import tls
from mitmproxy.proxy import commands
from mitmproxy.proxy import context
from mitmproxy.proxy import events
from mitmproxy.proxy import layer
from mitmproxy.proxy import tunnel
from mitmproxy.proxy.layers.tls import TlsClienthelloHook
from mitmproxy.proxy.layers.tls import TlsEstablishedClientHook
from mitmproxy.proxy.layers.tls import TlsEstablishedServerHook
from mitmproxy.proxy.layers.tls import TlsFailedClientHook
from mitmproxy.proxy.layers.tls import TlsFailedServerHook
from mitmproxy.proxy.layers.udp import UDPLayer
from mitmproxy.tls import ClientHelloData

SUPPORTED_QUIC_VERSIONS_SERVER = QuicConfiguration(is_client=False).supported_versions


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
                stream = self.quic._get_or_create_stream_for_send(command.stream_id)
                existing_reset_error_code = stream.sender._reset_error_code
                if existing_reset_error_code is None:
                    self.quic.reset_stream(command.stream_id, command.error_code)
                elif self.debug:  # pragma: no cover
                    yield commands.Log(
                        f"{self.debug}[quic] stream {stream.stream_id} already reset ({existing_reset_error_code=}, {command.error_code=})",
                        DEBUG,
                    )
            elif isinstance(command, StopSendingQuicStream):
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
                self.conn.tls_version = "QUICv1"

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
                        f"{self.debug}[quic] close_notify {self.conn} ({reason=!s})",
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
            elif isinstance(event, quic_events.StopSendingReceived):
                yield from self.event_to_child(
                    QuicStreamStopSending(self.conn, event.stream_id, event.error_code)
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
    handshake_datagram_buf: list[bytes]

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
        self.handshake_datagram_buf = []

    def start_handshake(self) -> layer.CommandGenerator[None]:
        yield from ()

    def receive_handshake_data(
        self, data: bytes
    ) -> layer.CommandGenerator[tuple[bool, str | None]]:
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
        if (
            header.version is not None
            and header.version not in SUPPORTED_QUIC_VERSIONS_SERVER
        ):
            yield commands.SendData(
                self.tunnel_connection,
                encode_quic_version_negotiation(
                    source_cid=header.destination_cid,
                    destination_cid=header.source_cid,
                    supported_versions=SUPPORTED_QUIC_VERSIONS_SERVER,
                ),
            )
            return False, None

        # ensure it's (likely) a client handshake packet
        if len(data) < 1200 or header.packet_type != PACKET_TYPE_INITIAL:
            return (
                False,
                f"Invalid handshake received, roaming not supported. ({data.hex()})",
            )

        self.handshake_datagram_buf.append(data)
        # extract the client hello
        try:
            client_hello = quic_parse_client_hello_from_datagrams(
                self.handshake_datagram_buf
            )
        except ValueError as e:
            msgs = b"\n".join(self.handshake_datagram_buf)
            dbg = f"Cannot parse ClientHello: {e} ({msgs.hex()})"
            self.handshake_datagram_buf.clear()
            return False, dbg

        if not client_hello:
            return False, None

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
            for dgm in self.handshake_datagram_buf:
                yield from parent_layer.handle_event(
                    events.DataReceived(self.context.client, dgm)
                )
            self.handshake_datagram_buf.clear()
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
        assert self.quic
        for dgm in self.handshake_datagram_buf:
            self.quic.receive_datagram(dgm, self.conn.peername, now=self._time())
        self.handshake_datagram_buf.clear()

        # handle events emanating from `self.quic`
        return (yield from super().receive_handshake_data(b""))

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
