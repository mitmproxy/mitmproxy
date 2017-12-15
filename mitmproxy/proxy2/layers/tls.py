import os
import struct
from typing import MutableMapping, Optional, Iterator, Union, Generator, Any

from OpenSSL import SSL

from mitmproxy.certs import CertStore
from mitmproxy.proxy.protocol import TlsClientHello
from mitmproxy.proxy.protocol import tls
from mitmproxy.proxy2 import context
from mitmproxy.proxy2 import layer, commands, events
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


def parse_client_hello(data: bytes) -> Optional[TlsClientHello]:
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
        return TlsClientHello(client_hello[4:])
    return None


class _TLSLayer(layer.Layer):
    send_buffer: MutableMapping[SSL.Connection, bytearray]
    tls: MutableMapping[context.Connection, SSL.Connection]
    child_layer: Optional[layer.Layer] = None

    def __init__(self, context):
        super().__init__(context)
        self.send_buffer = {}
        self.tls = {}

    def tls_interact(self, conn: context.Connection):
        while True:
            try:
                data = self.tls[conn].bio_read(65535)
            except SSL.WantReadError:
                # Okay, nothing more waiting to be sent.
                return
            else:
                yield commands.SendData(conn, data)

    def send(
            self,
            send_command: commands.SendData,
    ) -> commands.TCommandGenerator:
        tls_conn = self.tls[send_command.connection]
        if send_command.connection.tls_established:
            tls_conn.sendall(send_command.data)
            yield from self.tls_interact(send_command.connection)
        else:
            buf = self.send_buffer.setdefault(tls_conn, bytearray())
            buf.extend(send_command.data)

    def negotiate(self, event: events.DataReceived) -> Generator[commands.Command, Any, bool]:
        """
        Make sure to trigger processing if done!
        """
        # bio_write errors for b"", so we need to check first if we actually received something.
        tls_conn = self.tls[event.connection]
        if event.data:
            tls_conn.bio_write(event.data)
        try:
            tls_conn.do_handshake()
        except SSL.WantReadError:
            yield from self.tls_interact(event.connection)
            return False
        else:
            event.connection.tls_established = True
            event.connection.alpn = tls_conn.get_alpn_proto_negotiated()
            print(f"TLS established: {event.connection}")
            # TODO: Set all other connection attributes here
            # there might already be data in the OpenSSL BIO, so we need to trigger its processing.
            yield from self.relay(events.DataReceived(event.connection, b""))
            if tls_conn in self.send_buffer:
                data_to_send = bytes(self.send_buffer.pop(tls_conn))
                yield from self.send(commands.SendData(event.connection, data_to_send))
            return True

    def relay(self, event: events.DataReceived):
        tls_conn = self.tls[event.connection]
        if event.data:
            tls_conn.bio_write(event.data)
        yield from self.tls_interact(event.connection)

        plaintext = bytearray()
        while True:
            try:
                plaintext.extend(tls_conn.recv(65535))
            except (SSL.WantReadError, SSL.ZeroReturnError):
                break

        if plaintext:
            evt = events.DataReceived(event.connection, bytes(plaintext))
            # yield commands.Log(f"Plain{evt}")
            yield from self.event_to_child(evt)

    def event_to_child(self, event: events.Event) -> commands.TCommandGenerator:
        for command in self.child_layer.handle_event(event):
            if isinstance(command, commands.SendData) and command.connection in self.tls:
                yield from self.send(command)
            else:
                yield command


class ServerTLSLayer(_TLSLayer):
    """
    This layer manages TLS on potentially multiple server connections.
    """

    def __init__(self, context: context.Context):
        super().__init__(context)
        self.child_layer = layer.NextLayer(context)

    @expect(events.Start)
    def start(self, event: events.Start) -> commands.TCommandGenerator:
        yield from self.child_layer.handle_event(event)

        server = self.context.server
        if server.connected and server.tls:
            yield from self._start_tls(server)
        self._handle_event = self.process

    _handle_event = start

    def process(self, event: Union[events.DataReceived, events.ConnectionClosed]):
        if isinstance(event, events.DataReceived) and event.connection in self.tls:
            if not event.connection.tls_established:
                yield from self.negotiate(event)
            else:
                yield from self.relay(event)
        elif isinstance(event, events.OpenConnectionReply):
            err = event.reply
            conn = event.command.connection
            if not err and conn.tls:
                yield from self._start_tls(conn)
            yield from self.event_to_child(event)
        elif isinstance(event, events.ConnectionClosed):
            yield from self.event_to_child(event)
            self.send_buffer.pop(
                self.tls.pop(event.connection, None),
                None
            )
        else:
            yield from self.event_to_child(event)

    def _start_tls(self, server: context.Server):
        ssl_context = SSL.Context(SSL.SSLv23_METHOD)

        if server.alpn_offers:
            ssl_context.set_alpn_protos(server.alpn_offers)

        self.tls[server] = SSL.Connection(ssl_context)

        if server.sni:
            if server.sni is True:
                if self.context.client.sni:
                    server.sni = self.context.client.sni.encode("idna")
                else:
                    server.sni = server.address[0].encode("idna")
                    self.tls[server].set_tlsext_host_name(server.sni)
        self.tls[server].set_connect_state()

        yield from self.process(events.DataReceived(server, b""))


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
     │ Do we need server TLS info
     │ to establish TLS with client?
     │      ┌───────────────────┐
     ├─────→│Wait for Server TLS│
     │  yes └┬──────────────────┘
     │no     │
     ↓       ↓
    ┌────────────────┐
    │Process messages│
    └────────────────┘

    """
    recv_buffer: bytearray

    def __init__(self, context: context.Context):
        super().__init__(context)
        self.recv_buffer = bytearray()
        self.child_layer = ServerTLSLayer(self.context)

    @expect(events.Start)
    def state_start(self, _) -> commands.TCommandGenerator:
        self.context.client.tls = True
        self._handle_event = self.state_wait_for_clienthello
        yield from ()

    _handle_event = state_start

    @expect(events.DataReceived, events.ConnectionClosed)
    def state_wait_for_clienthello(self, event: events.Event):
        client = self.context.client
        server = self.context.server
        if isinstance(event, events.DataReceived) and event.connection == client:
            self.recv_buffer.extend(event.data)
            try:
                client_hello = parse_client_hello(self.recv_buffer)
            except ValueError as e:
                raise NotImplementedError() from e  # TODO

            if client_hello:
                yield commands.Log(f"Client Hello: {client_hello}")

                client.sni = client_hello.sni
                client.alpn_offers = client_hello.alpn_protocols

                client_tls_requires_server_connection = (
                        self.context.server.tls and
                        self.context.options.upstream_cert and
                        (
                                self.context.options.add_upstream_certs_to_client_chain or
                                client.alpn_offers or
                                not client.sni
                        )
                )

                # What do we do with the client connection now?
                if client_tls_requires_server_connection and not server.tls_established:
                    yield from self.start_server_tls()
                    self._handle_event = self.state_wait_for_server_tls
                else:
                    yield from self.start_negotiate()
                    self._handle_event = self.state_process
        else:
            raise NotImplementedError(event)  # TODO

    def state_wait_for_server_tls(self, event: events.Event):
        yield from self.event_to_child(event)
        # TODO: Handle case where TLS establishment fails.
        # We still need a good way to signal this - one possibility would be by closing
        # the connection?
        if self.context.server.tls_established:
            yield from self.start_negotiate()
            self._handle_event = self.state_process

    def state_process(self, event: events.Event):
        if isinstance(event, events.DataReceived) and event.connection == self.context.client:
            if not event.connection.tls_established:
                yield from self.negotiate(event)
            else:
                yield from self.relay(event)
        else:
            yield from self.event_to_child(event)

    def start_server_tls(self):
        """
        We often need information from the upstream connection to establish TLS with the client.
        For example, we need to check if the client does ALPN or not.
        """
        if not self.context.server.connected:
            err = yield commands.OpenConnection(self.context.server)
            if err:
                yield commands.Log(
                    "Cannot establish server connection, which is required to establish TLS with the client."
                )

        self.context.server.alpn_offers = [
            x for x in self.context.client.alpn_offers
            if not (x.startswith(b"h2-") or x.startswith(b"spdy"))
        ]

        yield from self.child_layer.handle_event(events.Start())

    def start_negotiate(self):
        if not self.child_layer:
            yield from self.child_layer.handle_event(events.Start())

        # FIXME: Do this properly
        client = self.context.client
        server = self.context.server
        context = SSL.Context(SSL.SSLv23_METHOD)
        cert, privkey, cert_chain = CertStore.from_store(
            os.path.expanduser("~/.mitmproxy"), "mitmproxy"
        ).get_cert(b"example.com", (b"example.com",))
        context.use_privatekey(privkey)
        context.use_certificate(cert.x509)
        context.set_cipher_list(tls.DEFAULT_CLIENT_CIPHERS)

        if server.alpn:
            def alpn_select_callback(conn_, options):
                if server.alpn in options:
                    return server.alpn

            context.set_alpn_select_callback(alpn_select_callback)

        self.tls[self.context.client] = SSL.Connection(context)
        self.tls[self.context.client].set_accept_state()

        yield from self.state_process(events.DataReceived(
            client, bytes(self.recv_buffer)
        ))
        self.recv_buffer = bytearray()
