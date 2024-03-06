import struct
import time
from collections.abc import Iterator
from dataclasses import dataclass
from logging import DEBUG
from logging import ERROR
from logging import INFO
from logging import WARNING

from OpenSSL import SSL

from mitmproxy import certs
from mitmproxy import connection
from mitmproxy.net.tls import starts_like_dtls_record
from mitmproxy.net.tls import starts_like_tls_record
from mitmproxy.proxy import commands
from mitmproxy.proxy import context
from mitmproxy.proxy import events
from mitmproxy.proxy import layer
from mitmproxy.proxy import tunnel
from mitmproxy.proxy.commands import StartHook
from mitmproxy.proxy.layers import tcp
from mitmproxy.proxy.layers import udp
from mitmproxy.tls import ClientHello
from mitmproxy.tls import ClientHelloData
from mitmproxy.tls import TlsData
from mitmproxy.utils import human


def handshake_record_contents(data: bytes) -> Iterator[bytes]:
    """
    Returns a generator that yields the bytes contained in each handshake record.
    This will raise an error on the first non-handshake record, so fully exhausting this
    generator is a bad idea.
    """
    offset = 0
    while True:
        if len(data) < offset + 5:
            return
        record_header = data[offset : offset + 5]
        if not starts_like_tls_record(record_header):
            raise ValueError(f"Expected TLS record, got {record_header!r} instead.")
        record_size = struct.unpack("!H", record_header[3:])[0]
        if record_size == 0:
            raise ValueError("Record must not be empty.")
        offset += 5

        if len(data) < offset + record_size:
            return
        record_body = data[offset : offset + record_size]
        yield record_body
        offset += record_size


def get_client_hello(data: bytes) -> bytes | None:
    """
    Read all TLS records that contain the initial ClientHello.
    Returns the raw handshake packet bytes, without TLS record headers.
    """
    client_hello = b""
    for d in handshake_record_contents(data):
        client_hello += d
        if len(client_hello) >= 4:
            client_hello_size = struct.unpack("!I", b"\x00" + client_hello[1:4])[0] + 4
            if len(client_hello) >= client_hello_size:
                return client_hello[:client_hello_size]
    return None


def parse_client_hello(data: bytes) -> ClientHello | None:
    """
    Check if the supplied bytes contain a full ClientHello message,
    and if so, parse it.

    Returns:
        - A ClientHello object on success
        - None, if the TLS record is not complete

    Raises:
        - A ValueError, if the passed ClientHello is invalid
    """
    # Check if ClientHello is complete
    client_hello = get_client_hello(data)
    if client_hello:
        try:
            return ClientHello(client_hello[4:])
        except EOFError as e:
            raise ValueError("Invalid ClientHello") from e
    return None


def dtls_handshake_record_contents(data: bytes) -> Iterator[bytes]:
    """
    Returns a generator that yields the bytes contained in each handshake record.
    This will raise an error on the first non-handshake record, so fully exhausting this
    generator is a bad idea.
    """
    offset = 0
    while True:
        # DTLS includes two new fields, totaling 8 bytes, between Version and Length
        if len(data) < offset + 13:
            return
        record_header = data[offset : offset + 13]
        if not starts_like_dtls_record(record_header):
            raise ValueError(f"Expected DTLS record, got {record_header!r} instead.")
        # Length fields starts at 11
        record_size = struct.unpack("!H", record_header[11:])[0]
        if record_size == 0:
            raise ValueError("Record must not be empty.")
        offset += 13

        if len(data) < offset + record_size:
            return
        record_body = data[offset : offset + record_size]
        yield record_body
        offset += record_size


def get_dtls_client_hello(data: bytes) -> bytes | None:
    """
    Read all DTLS records that contain the initial ClientHello.
    Returns the raw handshake packet bytes, without TLS record headers.
    """
    client_hello = b""
    for d in dtls_handshake_record_contents(data):
        client_hello += d
        if len(client_hello) >= 13:
            # comment about slicing: we skip the epoch and sequence number
            client_hello_size = (
                struct.unpack("!I", b"\x00" + client_hello[9:12])[0] + 12
            )
            if len(client_hello) >= client_hello_size:
                return client_hello[:client_hello_size]
    return None


def dtls_parse_client_hello(data: bytes) -> ClientHello | None:
    """
    Check if the supplied bytes contain a full ClientHello message,
    and if so, parse it.

    Returns:
        - A ClientHello object on success
        - None, if the TLS record is not complete

    Raises:
        - A ValueError, if the passed ClientHello is invalid
    """
    # Check if ClientHello is complete
    client_hello = get_dtls_client_hello(data)
    if client_hello:
        try:
            return ClientHello(client_hello[12:], dtls=True)
        except EOFError as e:
            raise ValueError("Invalid ClientHello") from e
    return None


HTTP1_ALPNS = (b"http/1.1", b"http/1.0", b"http/0.9")
HTTP_ALPNS = (b"h2",) + HTTP1_ALPNS


# We need these classes as hooks can only have one argument at the moment.


@dataclass
class TlsClienthelloHook(StartHook):
    """
    Mitmproxy has received a TLS ClientHello message.

    This hook decides whether a server connection is needed
    to negotiate TLS with the client (data.establish_server_tls_first)
    """

    data: ClientHelloData


@dataclass
class TlsStartClientHook(StartHook):
    """
    TLS negotation between mitmproxy and a client is about to start.

    An addon is expected to initialize data.ssl_conn.
    (by default, this is done by `mitmproxy.addons.tlsconfig`)
    """

    data: TlsData


@dataclass
class TlsStartServerHook(StartHook):
    """
    TLS negotation between mitmproxy and a server is about to start.

    An addon is expected to initialize data.ssl_conn.
    (by default, this is done by `mitmproxy.addons.tlsconfig`)
    """

    data: TlsData


@dataclass
class TlsEstablishedClientHook(StartHook):
    """
    The TLS handshake with the client has been completed successfully.
    """

    data: TlsData


@dataclass
class TlsEstablishedServerHook(StartHook):
    """
    The TLS handshake with the server has been completed successfully.
    """

    data: TlsData


@dataclass
class TlsFailedClientHook(StartHook):
    """
    The TLS handshake with the client has failed.
    """

    data: TlsData


@dataclass
class TlsFailedServerHook(StartHook):
    """
    The TLS handshake with the server has failed.
    """

    data: TlsData


class TLSLayer(tunnel.TunnelLayer):
    tls: SSL.Connection = None  # type: ignore
    """The OpenSSL connection object"""

    def __init__(self, context: context.Context, conn: connection.Connection):
        super().__init__(
            context,
            tunnel_connection=conn,
            conn=conn,
        )

        conn.tls = True

    def __repr__(self):
        return (
            super().__repr__().replace(")", f" {self.conn.sni!r} {self.conn.alpn!r})")
        )

    @property
    def is_dtls(self):
        return self.conn.transport_protocol == "udp"

    @property
    def proto_name(self):
        return "DTLS" if self.is_dtls else "TLS"

    def start_tls(self) -> layer.CommandGenerator[None]:
        assert not self.tls

        tls_start = TlsData(self.conn, self.context, is_dtls=self.is_dtls)
        if self.conn == self.context.client:
            yield TlsStartClientHook(tls_start)
        else:
            yield TlsStartServerHook(tls_start)
        if not tls_start.ssl_conn:
            yield commands.Log(
                f"No {self.proto_name} context was provided, failing connection.", ERROR
            )
            yield commands.CloseConnection(self.conn)
            return
        assert tls_start.ssl_conn
        self.tls = tls_start.ssl_conn

    def tls_interact(self) -> layer.CommandGenerator[None]:
        while True:
            try:
                data = self.tls.bio_read(65535)
            except SSL.WantReadError:
                return  # Okay, nothing more waiting to be sent.
            else:
                yield commands.SendData(self.conn, data)

    def receive_handshake_data(
        self, data: bytes
    ) -> layer.CommandGenerator[tuple[bool, str | None]]:
        # bio_write errors for b"", so we need to check first if we actually received something.
        if data:
            self.tls.bio_write(data)
        try:
            self.tls.do_handshake()
        except SSL.WantReadError:
            yield from self.tls_interact()
            return False, None
        except SSL.Error as e:
            # provide more detailed information for some errors.
            last_err = (
                e.args and isinstance(e.args[0], list) and e.args[0] and e.args[0][-1]
            )
            if last_err in [
                (
                    "SSL routines",
                    "tls_process_server_certificate",
                    "certificate verify failed",
                ),
                ("SSL routines", "", "certificate verify failed"),  # OpenSSL 3+
            ]:
                verify_result = SSL._lib.SSL_get_verify_result(self.tls._ssl)  # type: ignore
                error = SSL._ffi.string(  # type: ignore
                    SSL._lib.X509_verify_cert_error_string(verify_result)  # type: ignore
                ).decode()
                err = f"Certificate verify failed: {error}"
            elif last_err in [
                ("SSL routines", "ssl3_read_bytes", "tlsv1 alert unknown ca"),
                ("SSL routines", "ssl3_read_bytes", "sslv3 alert bad certificate"),
                ("SSL routines", "ssl3_read_bytes", "ssl/tls alert bad certificate"),
                ("SSL routines", "", "tlsv1 alert unknown ca"),  # OpenSSL 3+
                ("SSL routines", "", "sslv3 alert bad certificate"),  # OpenSSL 3+
                ("SSL routines", "", "ssl/tls alert bad certificate"),  # OpenSSL 3.2+
            ]:
                assert isinstance(last_err, tuple)
                err = last_err[2]
            elif (
                last_err
                in [
                    ("SSL routines", "ssl3_get_record", "wrong version number"),
                    ("SSL routines", "", "wrong version number"),  # OpenSSL 3+
                    ("SSL routines", "", "packet length too long"),  # OpenSSL 3+
                    ("SSL routines", "", "record layer failure"),  # OpenSSL 3+
                ]
                and data[:4].isascii()
            ):
                err = f"The remote server does not speak TLS."
            elif last_err in [
                ("SSL routines", "ssl3_read_bytes", "tlsv1 alert protocol version"),
                ("SSL routines", "", "tlsv1 alert protocol version"),  # OpenSSL 3+
            ]:
                err = (
                    f"The remote server and mitmproxy cannot agree on a TLS version to use. "
                    f"You may need to adjust mitmproxy's tls_version_server_min option."
                )
            else:
                err = f"OpenSSL {e!r}"
            return False, err
        else:
            # Here we set all attributes that are only known *after* the handshake.

            # Get all peer certificates.
            # https://www.openssl.org/docs/man1.1.1/man3/SSL_get_peer_cert_chain.html
            # If called on the client side, the stack also contains the peer's certificate; if called on the server
            # side, the peer's certificate must be obtained separately using SSL_get_peer_certificate(3).
            all_certs = self.tls.get_peer_cert_chain() or []
            if self.conn == self.context.client:
                cert = self.tls.get_peer_certificate()
                if cert:
                    all_certs.insert(0, cert)

            self.conn.timestamp_tls_setup = time.time()
            self.conn.alpn = self.tls.get_alpn_proto_negotiated()
            self.conn.certificate_list = [
                certs.Cert.from_pyopenssl(x) for x in all_certs
            ]
            self.conn.cipher = self.tls.get_cipher_name()
            self.conn.tls_version = self.tls.get_protocol_version_name()
            if self.debug:
                yield commands.Log(
                    f"{self.debug}[tls] tls established: {self.conn}", DEBUG
                )
            if self.conn == self.context.client:
                yield TlsEstablishedClientHook(
                    TlsData(self.conn, self.context, self.tls)
                )
            else:
                yield TlsEstablishedServerHook(
                    TlsData(self.conn, self.context, self.tls)
                )
            yield from self.receive_data(b"")
            return True, None

    def on_handshake_error(self, err: str) -> layer.CommandGenerator[None]:
        self.conn.error = err
        if self.conn == self.context.client:
            yield TlsFailedClientHook(TlsData(self.conn, self.context, self.tls))
        else:
            yield TlsFailedServerHook(TlsData(self.conn, self.context, self.tls))
        yield from super().on_handshake_error(err)

    def receive_data(self, data: bytes) -> layer.CommandGenerator[None]:
        if data:
            self.tls.bio_write(data)
        yield from self.tls_interact()

        plaintext = bytearray()
        close = False
        while True:
            try:
                plaintext.extend(self.tls.recv(65535))
            except SSL.WantReadError:
                break
            except SSL.ZeroReturnError:
                close = True
                break
            except SSL.Error as e:
                # This may be happening because the other side send an alert.
                # There's somewhat ugly behavior with Firefox on Android here,
                # which upon mistrusting a certificate still completes the handshake
                # and then sends an alert in the next packet. At this point we have unfortunately
                # already fired out `tls_established_client` hook.
                yield commands.Log(f"TLS Error: {e}", WARNING)
                break
        if plaintext:
            yield from self.event_to_child(
                events.DataReceived(self.conn, bytes(plaintext))
            )
        if close:
            self.conn.state &= ~connection.ConnectionState.CAN_READ
            if self.debug:
                yield commands.Log(f"{self.debug}[tls] close_notify {self.conn}", DEBUG)
            yield from self.event_to_child(events.ConnectionClosed(self.conn))

    def receive_close(self) -> layer.CommandGenerator[None]:
        if self.tls.get_shutdown() & SSL.RECEIVED_SHUTDOWN:
            pass  # We have already dispatched a ConnectionClosed to the child layer.
        else:
            yield from super().receive_close()

    def send_data(self, data: bytes) -> layer.CommandGenerator[None]:
        try:
            self.tls.sendall(data)
        except (SSL.ZeroReturnError, SSL.SysCallError):
            # The other peer may still be trying to send data over, which we discard here.
            pass
        yield from self.tls_interact()

    def send_close(
        self, command: commands.CloseConnection
    ) -> layer.CommandGenerator[None]:
        # We should probably shutdown the TLS connection properly here.
        yield from super().send_close(command)


class ServerTLSLayer(TLSLayer):
    """
    This layer establishes TLS for a single server connection.
    """

    wait_for_clienthello: bool = False

    def __init__(self, context: context.Context, conn: connection.Server | None = None):
        super().__init__(context, conn or context.server)

    def start_handshake(self) -> layer.CommandGenerator[None]:
        wait_for_clienthello = (
            # if command_to_reply_to is set, we've been instructed to open the connection from the child layer.
            # in that case any potential ClientHello is already parsed (by the ClientTLS child layer).
            not self.command_to_reply_to
            # if command_to_reply_to is not set, the connection was already open when this layer received its Start
            # event (eager connection strategy). We now want to establish TLS right away, _unless_ we already know
            # that there's TLS on the client side as well (we check if our immediate child layer is set to be ClientTLS)
            # In this case want to wait for ClientHello to be parsed, so that we can incorporate SNI/ALPN from there.
            and isinstance(self.child_layer, ClientTLSLayer)
        )
        if wait_for_clienthello:
            self.wait_for_clienthello = True
            self.tunnel_state = tunnel.TunnelState.CLOSED
        else:
            yield from self.start_tls()
            if self.tls:
                yield from self.receive_handshake_data(b"")

    def event_to_child(self, event: events.Event) -> layer.CommandGenerator[None]:
        if self.wait_for_clienthello:
            for command in super().event_to_child(event):
                if (
                    isinstance(command, commands.OpenConnection)
                    and command.connection == self.conn
                ):
                    self.wait_for_clienthello = False
                    # swallow OpenConnection here by not re-yielding it.
                else:
                    yield command
        else:
            yield from super().event_to_child(event)

    def on_handshake_error(self, err: str) -> layer.CommandGenerator[None]:
        yield commands.Log(f"Server TLS handshake failed. {err}", level=WARNING)
        yield from super().on_handshake_error(err)


class ClientTLSLayer(TLSLayer):
    """
    This layer establishes TLS on a single client connection.

    ┌─────┐
    │Start│
    └┬────┘
     ↓
    ┌────────────────────┐
    │Wait for ClientHello│
    └┬───────────────────┘
     ↓
    ┌────────────────┐
    │Process messages│
    └────────────────┘

    """

    recv_buffer: bytearray
    server_tls_available: bool
    client_hello_parsed: bool = False

    def __init__(self, context: context.Context):
        if context.client.tls:
            # In the case of TLS-over-TLS, we already have client TLS. As the outer TLS connection between client
            # and proxy isn't that interesting to us, we just unset the attributes here and keep the inner TLS
            # session's attributes.
            # Alternatively we could create a new Client instance,
            # but for now we keep it simple. There is a proof-of-concept at
            # https://github.com/mitmproxy/mitmproxy/commit/9b6e2a716888b7787514733b76a5936afa485352.
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
        self.server_tls_available = isinstance(self.context.layers[-2], ServerTLSLayer)
        self.recv_buffer = bytearray()

    def start_handshake(self) -> layer.CommandGenerator[None]:
        yield from ()

    def receive_handshake_data(
        self, data: bytes
    ) -> layer.CommandGenerator[tuple[bool, str | None]]:
        if self.client_hello_parsed:
            return (yield from super().receive_handshake_data(data))
        self.recv_buffer.extend(data)
        try:
            if self.is_dtls:
                client_hello = dtls_parse_client_hello(self.recv_buffer)
            else:
                client_hello = parse_client_hello(self.recv_buffer)
        except ValueError:
            return False, f"Cannot parse ClientHello: {self.recv_buffer.hex()}"

        if client_hello:
            self.client_hello_parsed = True
        else:
            return False, None

        self.conn.sni = client_hello.sni
        self.conn.alpn_offers = client_hello.alpn_protocols
        tls_clienthello = ClientHelloData(self.context, client_hello)
        yield TlsClienthelloHook(tls_clienthello)

        if tls_clienthello.ignore_connection:
            # we've figured out that we don't want to intercept this connection, so we assign fake connection objects
            # to all TLS layers. This makes the real connection contents just go through.
            self.conn = self.tunnel_connection = connection.Client(
                peername=("ignore-conn", 0), sockname=("ignore-conn", 0)
            )
            parent_layer = self.context.layers[self.context.layers.index(self) - 1]
            if isinstance(parent_layer, ServerTLSLayer):
                parent_layer.conn = parent_layer.tunnel_connection = connection.Server(
                    address=None
                )
            if self.is_dtls:
                self.child_layer = udp.UDPLayer(self.context, ignore=True)
            else:
                self.child_layer = tcp.TCPLayer(self.context, ignore=True)
            yield from self.event_to_child(
                events.DataReceived(self.context.client, bytes(self.recv_buffer))
            )
            self.recv_buffer.clear()
            return True, None
        if (
            tls_clienthello.establish_server_tls_first
            and not self.context.server.tls_established
        ):
            err = yield from self.start_server_tls()
            if err:
                yield commands.Log(
                    f"Unable to establish {self.proto_name} connection with server ({err}). "
                    f"Trying to establish {self.proto_name} with client anyway. "
                    f"If you plan to redirect requests away from this server, "
                    f"consider setting `connection_strategy` to `lazy` to suppress early connections."
                )

        yield from self.start_tls()
        if not self.conn.connected:
            return False, "connection closed early"

        ret = yield from super().receive_handshake_data(bytes(self.recv_buffer))
        self.recv_buffer.clear()
        return ret

    def start_server_tls(self) -> layer.CommandGenerator[str | None]:
        """
        We often need information from the upstream connection to establish TLS with the client.
        For example, we need to check if the client does ALPN or not.
        """
        if not self.server_tls_available:
            return f"No server {self.proto_name} available."
        err = yield commands.OpenConnection(self.context.server)
        return err

    def on_handshake_error(self, err: str) -> layer.CommandGenerator[None]:
        if self.conn.sni:
            dest = self.conn.sni
        else:
            dest = human.format_address(self.context.server.address)
        level: int = WARNING
        if err.startswith("Cannot parse ClientHello"):
            pass
        elif (
            "('SSL routines', 'tls_early_post_process_client_hello', 'unsupported protocol')"
            in err
            or "('SSL routines', '', 'unsupported protocol')" in err  # OpenSSL 3+
        ):
            err = (
                f"Client and mitmproxy cannot agree on a TLS version to use. "
                f"You may need to adjust mitmproxy's tls_version_client_min option."
            )
        elif (
            "unknown ca" in err
            or "bad certificate" in err
            or "certificate unknown" in err
        ):
            err = (
                f"The client does not trust the proxy's certificate for {dest} ({err})"
            )
        elif err == "connection closed":
            err = (
                f"The client disconnected during the handshake. If this happens consistently for {dest}, "
                f"this may indicate that the client does not trust the proxy's certificate."
            )
            level = INFO
        elif err == "connection closed early":
            pass
        else:
            err = f"The client may not trust the proxy's certificate for {dest} ({err})"
        if err != "connection closed early":
            yield commands.Log(f"Client TLS handshake failed. {err}", level=level)
        yield from super().on_handshake_error(err)
        self.event_to_child = self.errored  # type: ignore

    def errored(self, event: events.Event) -> layer.CommandGenerator[None]:
        if self.debug is not None:
            yield commands.Log(
                f"{self.debug}[tls] Swallowing {event} as handshake failed.", DEBUG
            )


class MockTLSLayer(TLSLayer):
    """Mock layer to disable actual TLS and use cleartext in tests.

    Use like so:
        monkeypatch.setattr(tls, "ServerTLSLayer", tls.MockTLSLayer)
    """

    def __init__(self, ctx: context.Context):
        super().__init__(ctx, connection.Server(address=None))
