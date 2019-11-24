import struct
import time
from typing import Any, Dict, Generator, Iterator, Optional, Tuple

from OpenSSL import SSL

from mitmproxy import certs
from mitmproxy.net import tls as net_tls
from mitmproxy.proxy2 import commands, events, layer
from mitmproxy.proxy2 import context
from mitmproxy.proxy2.utils import expect
from mitmproxy.utils import human


def is_tls_handshake_record(d: bytes) -> bool:
    """
    Returns:
        True, if the passed bytes start with the TLS record magic bytes
        False, otherwise.
    """
    # TLS ClientHello magic, works for SSLv3, TLSv1.0, TLSv1.1, TLSv1.2.
    # TLS 1.3 mandates legacy_record_version to be 0x0301.
    # http://www.moserware.com/2009/06/first-few-milliseconds-of-https.html#client-hello
    return (
            len(d) >= 3 and
            d[0] == 0x16 and
            d[1] == 0x03 and
            0x0 <= d[2] <= 0x03
    )


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
        record_header = data[offset:offset + 5]
        if not is_tls_handshake_record(record_header):
            raise ValueError(f"Expected TLS record, got {record_header} instead.")
        record_size = struct.unpack("!H", record_header[3:])[0]
        if record_size == 0:
            raise ValueError("Record must not be empty.")
        offset += 5

        if len(data) < offset + record_size:
            return
        record_body = data[offset:offset + record_size]
        yield record_body
        offset += record_size


def get_client_hello(data: bytes) -> Optional[bytes]:
    """
    Read all TLS records that contain the initial ClientHello.
    Returns the raw handshake packet bytes, without TLS record headers.
    """
    client_hello = b""
    for d in handshake_record_contents(data):
        client_hello += d
        if len(client_hello) >= 4:
            client_hello_size = struct.unpack("!I", b'\x00' + client_hello[1:4])[0] + 4
            if len(client_hello) >= client_hello_size:
                return client_hello[:client_hello_size]
    return None


def parse_client_hello(data: bytes) -> Optional[net_tls.ClientHello]:
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
        return net_tls.ClientHello(client_hello[4:])
    return None


HTTP_ALPNS = (b"h2", b"http/1.1", b"http/1.0", b"http/0.9")


class EstablishServerTLS(commands.ConnectionCommand):
    """Establish TLS on the given connection.

    If TLS establishment fails, the connection will automatically be closed by the TLS layer."""
    connection: context.Server
    blocking = True


class EstablishServerTLSReply(events.CommandReply):
    command: EstablishServerTLS
    reply: Optional[str]
    """error message"""


class StartHookData:
    conn: context.Connection
    context: context.Context
    ssl_conn: Optional[SSL.Connection]

    def __init__(self, conn, context) -> None:
        self.conn = conn
        self.context = context
        self.ssl_conn = None


class ClientHelloHookData:
    context: context.Context
    establish_server_tls_first: bool

    def __init__(self, context) -> None:
        self.context = context
        self.establish_server_tls_first = False


class _TLSLayer(layer.Layer):
    tls: Dict[context.Connection, SSL.Connection]
    child_layer: layer.Layer
    ssl_context: Optional[SSL.Context] = None

    def __init__(self, context: context.Context):
        super().__init__(context)
        self.tls = {}

    def __repr__(self):
        if not self.tls:
            state = "inactive"
        else:
            conn_states = []
            for conn in self.tls:
                if conn.tls_established:
                    conn_states.append(f"passthrough {conn.sni} {conn.alpn}")
                else:
                    conn_states.append(f"negotiating {conn.sni} {conn.alpn}")
            state = ", ".join(conn_states)
        return f"{type(self).__name__}({state})"

    def start_tls(self, conn: context.Connection, initial_data: bytes = b""):
        assert conn not in self.tls
        assert conn.connected
        conn.tls = True

        tls_start = StartHookData(conn, self.context)
        yield commands.Hook("tls_start", tls_start)
        self.tls[conn] = tls_start.ssl_conn

        yield from self.negotiate(conn, initial_data)

    def tls_interact(self, conn: context.Connection) -> commands.TCommandGenerator:
        while True:
            try:
                data = self.tls[conn].bio_read(65535)
            except SSL.WantReadError:
                # Okay, nothing more waiting to be sent.
                return
            else:
                yield commands.SendData(conn, data)

    def negotiate(self, conn: context.Connection, data: bytes) -> Generator[
        commands.Command, Any, Tuple[bool, Optional[str]]]:
        # bio_write errors for b"", so we need to check first if we actually received something.
        if data:
            self.tls[conn].bio_write(data)
        try:
            self.tls[conn].do_handshake()
        except SSL.WantReadError:
            yield from self.tls_interact(conn)
            return False, None
        except SSL.Error as e:
            # provide more detailed information for some errors.
            last_err = e.args and isinstance(e.args[0], list) and e.args[0] and e.args[0][-1]
            if last_err == ('SSL routines', 'tls_process_server_certificate', 'certificate verify failed'):
                verify_result = SSL._lib.SSL_get_verify_result(self.tls[conn]._ssl)
                error = SSL._ffi.string(SSL._lib.X509_verify_cert_error_string(verify_result)).decode()
                err = f"Certificate verify failed: {error}"
            elif last_err in [
                ('SSL routines', 'ssl3_read_bytes', 'tlsv1 alert unknown ca'),
                ('SSL routines', 'ssl3_read_bytes', 'sslv3 alert bad certificate')
            ]:
                err = last_err[2]
            else:
                err = repr(e)
            yield from self.on_handshake_error(conn, err)
            return False, err
        else:
            # Get all peer certificates.
            # https://www.openssl.org/docs/man1.1.1/man3/SSL_get_peer_cert_chain.html
            # If called on the client side, the stack also contains the peer's certificate; if called on the server
            # side, the peer's certificate must be obtained separately using SSL_get_peer_certificate(3).
            all_certs = self.tls[conn].get_peer_cert_chain() or []
            if conn == self.context.client:
                cert = self.tls[conn].get_peer_certificate()
                if cert:
                    all_certs.insert(0, cert)

            conn.tls_established = True
            conn.sni = self.tls[conn].get_servername()
            conn.alpn = self.tls[conn].get_alpn_proto_negotiated()
            conn.certificate_chain = [certs.Cert(x) for x in all_certs]
            conn.cipher_list = self.tls[conn].get_cipher_list()
            conn.tls_version = self.tls[conn].get_protocol_version_name()
            conn.timestamp_tls_setup = time.time()
            yield commands.Log(f"TLS established: {conn}")
            yield from self.receive(conn, b"")
            return True, None

    def receive(self, conn: context.Connection, data: bytes):
        if data:
            self.tls[conn].bio_write(data)
        yield from self.tls_interact(conn)

        plaintext = bytearray()
        close = False
        while True:
            try:
                plaintext.extend(self.tls[conn].recv(65535))
            except SSL.WantReadError:
                break
            except SSL.ZeroReturnError:
                close = True
                break

        if plaintext:
            yield from self.event_to_child(
                events.DataReceived(conn, bytes(plaintext))
            )
        if close:
            conn.state &= ~context.ConnectionState.CAN_READ
            yield commands.Log(f"TLS close_notify {conn=}")
            yield from self.event_to_child(
                events.ConnectionClosed(conn)
            )

    def event_to_child(self, event: events.Event) -> commands.TCommandGenerator:
        for command in self.child_layer.handle_event(event):
            if isinstance(command, commands.SendData) and command.connection in self.tls:
                self.tls[command.connection].sendall(command.data)
                yield from self.tls_interact(command.connection)
            else:
                yield command

    def _handle_event(self, event: events.Event) -> commands.TCommandGenerator:
        if isinstance(event, events.DataReceived) and event.connection in self.tls:
            if not event.connection.tls_established:
                yield from self.negotiate(event.connection, event.data)
            else:
                yield from self.receive(event.connection, event.data)
        elif isinstance(event, events.ConnectionClosed) and event.connection in self.tls:
            if event.connection.tls_established:
                if self.tls[event.connection].get_shutdown() & SSL.RECEIVED_SHUTDOWN:
                    pass  # We have already dispatched a ConnectionClosed to the child layer.
                else:
                    yield from self.event_to_child(event)
            else:
                yield from self.on_handshake_error(event.connection, "connection closed without notice")
        else:
            yield from self.event_to_child(event)

    def on_handshake_error(self, conn: context.Connection, err: str) -> commands.TCommandGenerator:
        yield commands.CloseConnection(conn)


class ServerTLSLayer(_TLSLayer):
    """
    This layer manages TLS for  potentially multiple server connections.
    """
    command_to_reply_to: Dict[context.Connection, EstablishServerTLS]

    def __init__(self, context: context.Context):
        super().__init__(context)
        self.command_to_reply_to = {}
        self.child_layer = layer.NextLayer(self.context)

    def negotiate(self, conn: context.Connection, data: bytes) \
            -> Generator[commands.Command, Any, Tuple[bool, Optional[str]]]:
        done, err = yield from super().negotiate(conn, data)
        if done or err:
            cmd = self.command_to_reply_to.pop(conn)
            yield from self.event_to_child(EstablishServerTLSReply(cmd, err))
        return done, err

    def event_to_child(self, event: events.Event) -> commands.TCommandGenerator:
        for command in super().event_to_child(event):
            if isinstance(command, EstablishServerTLS):
                self.command_to_reply_to[command.connection] = command
                yield from self.start_tls(command.connection)
            else:
                yield command

    def on_handshake_error(self, conn: context.Connection, err: str) -> commands.TCommandGenerator:
        yield commands.Log(
            f"Server TLS handshake failed. {err}",
            level="warn"
        )
        yield from super().on_handshake_error(conn, err)


class ClientTLSLayer(_TLSLayer):
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

    def __init__(self, context: context.Context):
        assert isinstance(context.layers[-1], ServerTLSLayer)
        super().__init__(context)
        self.recv_buffer = bytearray()
        self.child_layer = layer.NextLayer(self.context)
        self._handle_event = self.state_start

    @expect(events.Start)
    def state_start(self, _) -> commands.TCommandGenerator:
        self.context.client.tls = True
        self._handle_event = self.state_wait_for_clienthello
        yield from ()

    def state_wait_for_clienthello(self, event: events.Event) -> commands.TCommandGenerator:
        client = self.context.client
        if isinstance(event, events.DataReceived) and event.connection == client:
            self.recv_buffer.extend(event.data)
            try:
                client_hello = parse_client_hello(self.recv_buffer)
            except ValueError:
                yield commands.Log(f"Cannot parse ClientHello: {self.recv_buffer.hex()}")
                yield commands.CloseConnection(client)
                return

            if client_hello:
                client.sni = client_hello.sni
                client.alpn_offers = client_hello.alpn_protocols
                tls_clienthello = ClientHelloHookData(self.context)
                yield commands.Hook("tls_clienthello", tls_clienthello)

                if tls_clienthello.establish_server_tls_first and not self.context.server.tls_established:
                    err = yield from self.start_server_tls()
                    if err:
                        yield commands.Log("Unable to establish TLS connection with server. "
                                           "Trying to establish TLS with client anyway.")

                yield from self.start_tls(client, bytes(self.recv_buffer))
                self.recv_buffer.clear()
                self._handle_event = super()._handle_event

                # In any case, we now have enough information to start server TLS if needed.
                yield from self.event_to_child(events.Start())
        else:
            yield from self.event_to_child(event)

    def start_server_tls(self):
        """
        We often need information from the upstream connection to establish TLS with the client.
        For example, we need to check if the client does ALPN or not.
        """
        server = self.context.server
        if not server.connected:
            err = yield commands.OpenConnection(server)
            if err:
                yield commands.Log(
                    f"Cannot establish server connection: {err}"
                )
                return err

        err = yield EstablishServerTLS(server)
        if err:
            yield commands.Log(
                f"Cannot establish TLS with server: {err}"
            )
            return err

    def on_handshake_error(self, conn: context.Connection, err: str) -> commands.TCommandGenerator:
        if conn.sni:
            dest = conn.sni.decode("idna")
        else:
            dest = human.format_address(self.context.server.address)
        if "unknown ca" in err or "bad certificate" in err:
            keyword = "does not"
        else:
            keyword = "may not"
        yield commands.Log(
            f"Client TLS handshake failed. "
            f"The client {keyword} trust the proxy's certificate for {dest} ({err})",
            level="warn"
        )
        yield from super().on_handshake_error(conn, err)
