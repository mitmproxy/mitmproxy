import struct
import time
from dataclasses import dataclass
from typing import Iterator, Optional, Tuple

from OpenSSL import SSL

from mitmproxy import certs
from mitmproxy.net import tls as net_tls
from mitmproxy.proxy2 import commands, events, layer
from mitmproxy.proxy2 import context
from mitmproxy.proxy2.commands import Hook
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


# We need these classes as hooks can only have one argument at the moment.

@dataclass
class TlsStartData:
    conn: context.Connection
    context: context.Context
    ssl_conn: Optional[SSL.Connection] = None


@dataclass
class ClientHelloData:
    context: context.Context
    establish_server_tls_first: bool = False


class TlsStartHook(Hook):
    data: TlsStartData


class TlsClienthelloHook(Hook):
    data: ClientHelloData


class _TLSLayer(layer.Layer):
    conn: context.Connection
    """The connection for which we do TLS"""
    tls: SSL.Connection = None
    """The OpenSSL connection object"""
    child_layer: layer.Layer

    def __init__(self, context: context.Context, conn: context.Connection):
        super().__init__(context)
        self.conn = conn

    def __repr__(self):
        if not self.tls:
            state = "inactive"
        elif self.conn.tls_established:
            state = f"passthrough {self.conn.sni} {self.conn.alpn}"
        else:
            state = f"negotiating {self.conn.sni} {self.conn.alpn}"
        return f"{type(self).__name__}({state})"

    def start_tls(self, initial_data: bytes = b""):
        assert not self.tls
        assert self.conn.connected
        self.conn.tls = True

        tls_start = TlsStartData(self.conn, self.context)
        yield TlsStartHook(tls_start)
        assert tls_start.ssl_conn
        self.tls = tls_start.ssl_conn

        yield from self.negotiate(initial_data)

    def tls_interact(self) -> layer.CommandGenerator[None]:
        while True:
            try:
                data = self.tls.bio_read(65535)
            except SSL.WantReadError:
                # Okay, nothing more waiting to be sent.
                return
            else:
                yield commands.SendData(self.conn, data)

    def negotiate(self, data: bytes) -> layer.CommandGenerator[Tuple[bool, Optional[str]]]:
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
            last_err = e.args and isinstance(e.args[0], list) and e.args[0] and e.args[0][-1]
            if last_err == ('SSL routines', 'tls_process_server_certificate', 'certificate verify failed'):
                verify_result = SSL._lib.SSL_get_verify_result(self.tls._ssl)
                error = SSL._ffi.string(SSL._lib.X509_verify_cert_error_string(verify_result)).decode()
                err = f"Certificate verify failed: {error}"
            elif last_err in [
                ('SSL routines', 'ssl3_read_bytes', 'tlsv1 alert unknown ca'),
                ('SSL routines', 'ssl3_read_bytes', 'sslv3 alert bad certificate')
            ]:
                err = last_err[2]
            else:
                err = repr(e)
            yield from self.on_handshake_error(err)
            return False, err
        else:
            # Get all peer certificates.
            # https://www.openssl.org/docs/man1.1.1/man3/SSL_get_peer_cert_chain.html
            # If called on the client side, the stack also contains the peer's certificate; if called on the server
            # side, the peer's certificate must be obtained separately using SSL_get_peer_certificate(3).
            all_certs = self.tls.get_peer_cert_chain() or []
            if self.conn == self.context.client:
                cert = self.tls.get_peer_certificate()
                if cert:
                    all_certs.insert(0, cert)

            self.conn.tls_established = True
            self.conn.sni = self.tls.get_servername()
            self.conn.alpn = self.tls.get_alpn_proto_negotiated()
            self.conn.certificate_chain = [certs.Cert(x) for x in all_certs]
            self.conn.cipher_list = self.tls.get_cipher_list()
            self.conn.tls_version = self.tls.get_protocol_version_name()
            self.conn.timestamp_tls_setup = time.time()
            yield commands.Log(f"TLS established: {self.conn}")
            yield from self.receive(b"")
            return True, None

    def receive(self, data: bytes):
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

        if plaintext:
            yield from self.event_to_child(
                events.DataReceived(self.conn, bytes(plaintext))
            )
        if close:
            self.conn.state &= ~context.ConnectionState.CAN_READ
            yield commands.Log(f"TLS close_notify {self.conn}")
            yield from self.event_to_child(
                events.ConnectionClosed(self.conn)
            )

    def event_to_child(self, event: events.Event) -> layer.CommandGenerator[None]:
        for command in self.child_layer.handle_event(event):
            if isinstance(command, commands.SendData) and command.connection == self.conn:
                self.tls.sendall(command.data)
                yield from self.tls_interact()
            else:
                yield command

    def _handle_event(self, event: events.Event) -> layer.CommandGenerator[None]:
        if isinstance(event, events.DataReceived) and event.connection == self.conn:
            if not event.connection.tls_established:
                yield from self.negotiate(event.data)
            else:
                yield from self.receive(event.data)
        elif isinstance(event, events.ConnectionClosed) and event.connection == self.conn:
            if event.connection.tls_established:
                if self.tls.get_shutdown() & SSL.RECEIVED_SHUTDOWN:
                    pass  # We have already dispatched a ConnectionClosed to the child layer.
                else:
                    yield from self.event_to_child(event)
            else:
                yield from self.on_handshake_error("connection closed without notice")
        else:
            yield from self.event_to_child(event)

    def on_handshake_error(self, err: str) -> layer.CommandGenerator[None]:
        yield commands.CloseConnection(self.conn)


class ServerTLSLayer(_TLSLayer):
    """
    This layer establishes TLS for a single server connection.
    """
    command_to_reply_to: Optional[commands.OpenConnection] = None

    def __init__(self, context: context.Context):
        super().__init__(context, context.server)
        self.child_layer = layer.NextLayer(self.context)

    @expect(events.Start)
    def state_start(self, _) -> layer.CommandGenerator[None]:
        self.context.server.tls = True
        if self.context.server.connected:
            yield from self.start_tls()
        self._handle_event = super()._handle_event

    _handle_event = state_start

    def negotiate(self, data: bytes) -> layer.CommandGenerator[Tuple[bool, Optional[str]]]:
        done, err = yield from super().negotiate(data)
        if done or err:
            cmd = self.command_to_reply_to
            yield from self.event_to_child(events.OpenConnectionReply(cmd, err))
            self.command_to_reply_to = None
        return done, err

    def event_to_child(self, event: events.Event) -> layer.CommandGenerator[None]:
        for command in super().event_to_child(event):
            if isinstance(command, commands.OpenConnection) and command.connection == self.context.server:
                # create our own OpenConnection command object that blocks here.
                err = yield commands.OpenConnection(command.connection)
                if err:
                    yield from self.event_to_child(events.OpenConnectionReply(command, err))
                else:
                    self.command_to_reply_to = command
                    yield from self.start_tls()
            else:
                yield command

    def on_handshake_error(self, err: str) -> layer.CommandGenerator[None]:
        yield commands.Log(
            f"Server TLS handshake failed. {err}",
            level="warn"
        )
        yield from super().on_handshake_error(err)


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
        super().__init__(context, self.context.client)
        self.recv_buffer = bytearray()
        self.child_layer = layer.NextLayer(self.context)

    @expect(events.Start)
    def state_start(self, _) -> layer.CommandGenerator[None]:
        self.context.client.tls = True
        self._handle_event = self.state_wait_for_clienthello
        yield from ()

    _handle_event = state_start

    def state_wait_for_clienthello(self, event: events.Event) -> layer.CommandGenerator[None]:
        if isinstance(event, events.DataReceived) and event.connection == self.conn:
            self.recv_buffer.extend(event.data)
            try:
                client_hello = parse_client_hello(self.recv_buffer)
            except ValueError:
                yield commands.Log(f"Cannot parse ClientHello: {self.recv_buffer.hex()}")
                yield commands.CloseConnection(self.conn)
                return

            if client_hello:
                self.conn.sni = client_hello.sni
                self.conn.alpn_offers = client_hello.alpn_protocols
                tls_clienthello = ClientHelloData(self.context)
                yield TlsClienthelloHook(tls_clienthello)

                if tls_clienthello.establish_server_tls_first and not self.context.server.tls_established:
                    err = yield from self.start_server_tls()
                    if err:
                        yield commands.Log("Unable to establish TLS connection with server. "
                                           "Trying to establish TLS with client anyway.")

                yield from self.start_tls(bytes(self.recv_buffer))
                self.recv_buffer.clear()
                self._handle_event = super()._handle_event

                # In any case, we now have enough information to start server TLS if needed.
                yield from self.event_to_child(events.Start())
        else:
            yield from self.event_to_child(event)

    def start_server_tls(self) -> layer.CommandGenerator[Optional[str]]:
        """
        We often need information from the upstream connection to establish TLS with the client.
        For example, we need to check if the client does ALPN or not.
        """
        err = yield commands.OpenConnection(self.context.server)
        if err:
            yield commands.Log(f"Cannot establish server connection: {err}")
            return err
        else:
            return None

    def on_handshake_error(self, err: str) -> layer.CommandGenerator[None]:
        if self.conn.sni:
            dest = self.conn.sni.decode("idna")
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
        yield from super().on_handshake_error(err)
