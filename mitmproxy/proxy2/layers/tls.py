import os
import struct
from typing import Any, Generator, Iterator, Optional

from OpenSSL import SSL

from mitmproxy.certs import CertStore
from mitmproxy.net.tls import ClientHello
from mitmproxy.proxy.protocol import tls
from mitmproxy.proxy2 import commands, events, layer
from mitmproxy.proxy2 import context
from mitmproxy.proxy2.utils import expect


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


def parse_client_hello(data: bytes) -> Optional[ClientHello]:
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
        return ClientHello(client_hello[4:])
    return None


class EstablishServerTLS(commands.ConnectionCommand):
    connection: context.Server
    blocking = True


class EstablishServerTLSReply(events.CommandReply):
    command: EstablishServerTLS
    reply: Optional[str]
    """error message"""


class _TLSLayer(layer.Layer):
    conn: Optional[context.Connection] = None
    tls_conn: Optional[SSL.Connection] = None
    child_layer: layer.Layer

    def __repr__(self):
        if self.conn is None:
            state = "inactive"
        elif self.conn.tls_established:
            state = f"passthrough {self.conn.sni}, {self.conn.alpn}"
        else:
            state = f"negotiating {self.conn.sni}, {self.conn.alpn}"
        return f"{type(self).__name__}({state})"

    def tls_interact(self):
        while True:
            try:
                data = self.tls_conn.bio_read(65535)
            except SSL.WantReadError:
                # Okay, nothing more waiting to be sent.
                return
            else:
                yield commands.SendData(self.conn, data)

    def negotiate(self, data: bytes) -> Generator[commands.Command, Any, bool]:
        # bio_write errors for b"", so we need to check first if we actually received something.
        if data:
            self.tls_conn.bio_write(data)
        try:
            self.tls_conn.do_handshake()
        except SSL.WantReadError:
            yield from self.tls_interact()
            return False
        except SSL.ZeroReturnError:
            raise  # TODO: Figure out what to do when handshake fails.
        else:
            self.conn.tls_established = True
            self.conn.alpn = self.tls_conn.get_alpn_proto_negotiated()
            yield commands.Log(f"TLS established: {self.conn}")
            yield from self.receive(b"")
            # TODO: Set all other connection attributes here
            # there might already be data in the OpenSSL BIO, so we need to trigger its processing.
            return True

    def receive(self, data: bytes):
        if data:
            self.tls_conn.bio_write(data)
        yield from self.tls_interact()

        plaintext = bytearray()
        while True:
            try:
                plaintext.extend(self.tls_conn.recv(65535))
            except (SSL.WantReadError, SSL.ZeroReturnError):
                break

        if plaintext:
            evt = events.DataReceived(self.conn, bytes(plaintext))
            yield from self.event_to_child(evt)

    def event_to_child(self, event: events.Event) -> commands.TCommandGenerator:
        for command in self.child_layer.handle_event(event):
            if isinstance(command, commands.SendData) and command.connection == self.conn:
                self.tls_conn.sendall(command.data)
                yield from self.tls_interact()
            else:
                yield command

    def _handle_event(self, event: events.Event) -> commands.TCommandGenerator:
        if isinstance(event, events.DataReceived) and event.connection == self.conn:
            if not self.conn.tls_established:
                yield from self.negotiate(event.data)
            else:
                yield from self.receive(event.data)
        else:
            yield from self.event_to_child(event)


class ServerTLSLayer(_TLSLayer):
    """
    This layer manages TLS for a single server connection.
    """
    command_to_reply_to: Optional[EstablishServerTLS] = None

    def __init__(self, context: context.Context):
        super().__init__(context)
        self.child_layer = layer.NextLayer(self.context)

    def negotiate(self, data: bytes) -> Generator[commands.Command, Any, bool]:
        done = yield from super().negotiate(data)
        if done:
            assert self.command_to_reply_to
            yield from self.event_to_child(EstablishServerTLSReply(self.command_to_reply_to, None))
            self.command_to_reply_to = None
        return done

    def event_to_child(self, event: events.Event) -> commands.TCommandGenerator:
        for command in super().event_to_child(event):
            if isinstance(command, EstablishServerTLS):
                assert isinstance(command.connection, context.Server)
                assert not self.command_to_reply_to
                self.command_to_reply_to = command
                yield from self.start_server_tls(command.connection)
            else:
                yield command

    def start_server_tls(self, server: context.Server):
        ssl_context = SSL.Context(SSL.SSLv23_METHOD)
        if server.alpn_offers:
            ssl_context.set_alpn_protos(server.alpn_offers)

        assert not self.conn or not self.conn.connected
        assert server.connected
        self.conn = server
        self.tls_conn = SSL.Connection(ssl_context)

        if server.sni:
            if server.sni is True:
                if self.context.client.sni:
                    server.sni = self.context.client.sni
                else:
                    server.sni = server.address[0]
            self.tls_conn.set_tlsext_host_name(server.sni)
        self.tls_conn.set_connect_state()

        yield from self.negotiate(b"")


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
        self.conn = context.client
        self.recv_buffer = bytearray()
        self.child_layer = layer.NextLayer(self.context)

    @expect(events.Start)
    def state_start(self, _) -> commands.TCommandGenerator:
        self.context.client.tls = True
        self._handle_event = self.state_wait_for_clienthello
        yield from ()

    _handle_event = state_start

    @expect(events.DataReceived, events.ConnectionClosed)
    def state_wait_for_clienthello(self, event: events.Event):
        client = self.context.client
        if isinstance(event, events.DataReceived) and event.connection == client:
            self.recv_buffer.extend(event.data)
            try:
                client_hello = parse_client_hello(self.recv_buffer)
            except ValueError as e:
                raise NotImplementedError() from e  # TODO

            if client_hello:
                yield commands.Log(f"Client Hello: {client_hello}")

                # TODO: Don't do double conversion
                client.sni = client_hello.sni.encode("idna")
                client.alpn_offers = client_hello.alpn_protocols

                client_tls_requires_server_connection = (
                        self.context.server and
                        self.context.server.tls and
                        self.context.options.upstream_cert and
                        (
                                self.context.options.add_upstream_certs_to_client_chain or
                                # client.alpn_offers or
                                not client.sni
                        )
                )

                # What do we do with the client connection now?
                if client_tls_requires_server_connection and not self.context.server.tls_established:
                    err = yield from self.start_server_tls()
                    if err:
                        raise NotImplementedError

                yield from self.start_client_tls()
                self._handle_event = super()._handle_event

                # In any case, we now have enough information to start server TLS if needed.
                yield from self.event_to_child(events.Start())
        else:
            raise NotImplementedError(event)  # TODO

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
                    "Cannot establish server connection, which is required to establish TLS with the client."
                )
                return err

        server.alpn_offers = [
            x for x in self.context.client.alpn_offers
            if not (x.startswith(b"h2-") or x.startswith(b"spdy"))
        ]

        err = yield EstablishServerTLS(server)
        if err:
            yield commands.Log(
                "Cannot establish TLS with server, which is required to establish TLS with the client."
            )
            return err

    def start_client_tls(self):
        # FIXME: Do this properly. Also adjust error message in negotiate()
        client = self.context.client
        server = self.context.server
        context = SSL.Context(SSL.SSLv23_METHOD)
        cert, privkey, cert_chain = CertStore.from_store(
            os.path.expanduser("~/.mitmproxy"), "mitmproxy",
            self.context.options.key_size
        ).get_cert(client.sni, (client.sni,))
        context.use_privatekey(privkey)
        context.use_certificate(cert.x509)
        context.set_cipher_list(tls.DEFAULT_CLIENT_CIPHERS)

        def alpn_select_callback(conn_, options):
            if server.alpn in options:
                return server.alpn
            elif b"h2" in options:
                return b"h2"
            elif b"http/1.1" in options:
                return b"http/1.1"
            elif b"http/1.0" in options:
                return b"http/1.0"
            elif b"http/0.9" in options:
                return b"http/0.9"
            else:
                # FIXME: We MUST return something here. At this point we are at loss.
                return options[0]

        context.set_alpn_select_callback(alpn_select_callback)

        self.tls_conn = SSL.Connection(context)
        self.tls_conn.set_accept_state()

        yield from self.negotiate(bytes(self.recv_buffer))
        self.recv_buffer = None

    def negotiate(self, data: bytes) -> Generator[commands.Command, Any, bool]:
        try:
            done = yield from super().negotiate(data)
            return done
        except SSL.ZeroReturnError:
            yield commands.Log(
                f"Client TLS Handshake failed. "
                f"The client may not trust the proxy's certificate (SNI: {self.context.client.sni})."
                # TODO: Also use other sources than SNI
            )
            yield commands.CloseConnection(self.context.client)
