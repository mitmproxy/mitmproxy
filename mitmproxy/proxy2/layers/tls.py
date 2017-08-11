import os
from enum import Enum
import struct
from typing import MutableMapping, Generator, Optional

from OpenSSL import SSL

from mitmproxy import exceptions
from mitmproxy.certs import CertStore
from mitmproxy.proxy.protocol import TlsClientHello
from mitmproxy.proxy.protocol import tls
from mitmproxy.proxy2 import context
from mitmproxy.proxy2 import layer, commands, events
from mitmproxy.proxy2.utils import expect


class ConnectionState(Enum):
    NO_TLS = 1
    WAIT_FOR_CLIENTHELLO = 2
    WAIT_FOR_SERVER_TLS = 3
    WAIT_FOR_OPENCONNECTION = 4
    NEGOTIATING = 5
    ESTABLISHED = 6


def get_client_hello(client_conn):
    """
    Read all records from client buffer that contain the initial client hello message.

    client_conn:
        bytearray

    Returns:
        The raw handshake packet bytes, without TLS record header(s).
    """
    client_hello = b""
    client_hello_size = 1
    offset = 0
    while len(client_hello) < client_hello_size:
        record_header = client_conn[offset:5]
        if not tls.is_tls_record_magic(record_header) or len(record_header) != 5:
            raise exceptions.TlsProtocolException('Expected TLS record, got "%s" instead.' % record_header)
        record_size = struct.unpack("!H", record_header[3:])[0] + 5
        record_body = client_conn[offset + 5: record_size]
        if len(record_body) != record_size - 5:
            raise exceptions.TlsProtocolException("Unexpected EOF in TLS handshake: %s" % record_body)
        client_hello += record_body
        offset += record_size
        client_hello_size = struct.unpack("!I", b'\x00' + client_hello[1:4])[0] + 4
    return client_hello


class TLSLayer(layer.Layer):
    """
    The TLS layer manages both client- and server-side TLS connection state.
    This unfortunately is quite complex as the client handshake may depend on the server
    handshake and vice versa: We need the client's SNI and ALPN to connect upstream,
    and we need the server's ALPN choice to complete our client TLS handshake.
    On top, we may have configurations where TLS is only added on one end,
    and we also may have OpenConnection events which change the server's TLS configuration.


    The following state machine shows the possible states for client and server connection:

    Legend:
        /:   NO_TLS
        WCH: WAIT_FOR_CLIENTHELLO
        WST: WAIT_FOR_SERVER_TLS
        WOC: WAIT_FOR_OPENCONNECTION
        N:   NEGOTIATING
        E:   ESTABLISHED

    +------------+          +---+             +------------+          +---+<--+
    |Client State|--------->| / |             |Server State|--------->+ / |   |
    +------------+  no tls  +---+             +------------+  no tls  +---+   |
      |                                         |server tls             |     |
      |client tls                               |          OpenConn(TLS)|     |OpenConn(no TLS)
      v                                         v                       v     |
      +------------------------------+          +-------------------->+---+   |
      |  no server tls               |          |  no client tls      | N |   |
      |                              |          |                  +->+---+-->+
      |server tls                    v          |client tls        |    |     |
      v                      +---->+---+        |                  |    |     |
    +---+                    |     | N |        v                  |    v     |
    |WCH|                    |  +->+---+      +---+                |  +---+   |
    +---+                    |  |    |        |WCH|                |  | E |-->+
      |                      |  |    v        +---+                |  +---+   |
      |ClientHello arrives   |  |  +---+        |                  |          |
      |                      |  |  | E |        |ClientHello       +<----+    |
      +----------------------+  |  +---+        |arrives           |     |    |
      |  no server info needed  |               v                  |     |    |
      |                         |               +------------------+     |    |
      |server info needed       |               | already connected      |    |
      v                         |               | or server info needed  |    |
    +---+                       |               |                        |    |
    |WST|-----------------------+               |not needed              |    |
    +---+  server tls established               v                   (TLS)|    |(no TLS)
           (or errored)                       +---+                      |    |
                                              |WOC+--------------------->+----+
                                              +---+            OpenConn
    """
    tls: MutableMapping[context.Connection, SSL.Connection]
    state: MutableMapping[context.Connection, ConnectionState]
    recv_buffer: MutableMapping[context.Connection, bytearray]
    client_hello: Optional[TlsClientHello]

    child_layer: layer.Layer

    def __init__(self, context: context.Context):
        super().__init__(context)
        self.tls = {}
        self.state = {}
        self.recv_buffer = {
            context.client: bytearray(),
            context.server: bytearray()
        }
        self.client_hello = None

        self.child_layer = layer.NextLayer(context)

    @expect(events.Start)
    def start(self, _) -> commands.TCommandGenerator:
        client = self.context.client
        server = self.context.server

        if client.tls and server.tls:
            self.state[client] = ConnectionState.WAIT_FOR_CLIENTHELLO
            self.state[server] = ConnectionState.WAIT_FOR_CLIENTHELLO
        elif client.tls:
            yield from self.start_client_tls()
            self.state[server] = ConnectionState.NO_TLS
        elif server.tls and server.connected:
            self.state[client] = ConnectionState.NO_TLS
            yield from self.start_server_tls()
        else:
            self.state[client] = ConnectionState.NO_TLS
            self.state[server] = ConnectionState.NO_TLS

        yield from self.child_layer.handle_event(events.Start())
        self._handle_event = self.process

    _handle_event = start

    def send(self, send_command: commands.SendData) -> commands.TCommandGenerator:
        if self.state[send_command.connection] == ConnectionState.NO_TLS:
            yield send_command
        else:
            self.tls[send_command.connection].sendall(send_command.data)
            yield from self.tls_interact(send_command.connection)

    def event_to_child(self, event: events.Event) -> commands.TCommandGenerator:
        for command in self.child_layer.handle_event(event):
            if isinstance(command, commands.SendData):
                yield commands.Log(f"Plain{command}")
                yield from self.send(command)
            elif isinstance(command, commands.OpenConnection):
                raise NotImplementedError()
            else:
                yield command

    def recv(self, recv_event: events.DataReceived) -> Generator[commands.Command, None, bytes]:
        if self.state[recv_event.connection] == ConnectionState.NO_TLS:
            return recv_event.data
        else:
            if recv_event.data:
                self.tls[recv_event.connection].bio_write(recv_event.data)
            yield from self.tls_interact(recv_event.connection)

            recvd = bytearray()
            while True:
                try:
                    recvd.extend(self.tls[recv_event.connection].recv(65535))
                except (SSL.WantReadError, SSL.ZeroReturnError):
                    return bytes(recvd)

    def parse_client_hello(self):
        # Check if ClientHello is complete
        try:
            client_hello = get_client_hello(self.recv_buffer[self.context.client])[4:]
            self.client_hello = TlsClientHello(client_hello)
        except exceptions.TlsProtocolException:
            return False
        except EOFError as e:
            raise exceptions.TlsProtocolException(
                f'Cannot parse Client Hello: {e}, Raw Client Hello: {client_hello}'
            )
        else:
            return True

    def process(self, event: events.Event):
        if isinstance(event, events.DataReceived):
            state = self.state[event.connection]

            if state is ConnectionState.WAIT_FOR_CLIENTHELLO:
                yield from self.process_wait_for_clienthello(event)
            elif state is ConnectionState.WAIT_FOR_SERVER_TLS:
                self.recv_buffer[self.context.client].extend(event.data)
            elif state is ConnectionState.NEGOTIATING:
                yield from self.process_negotiate(event)
            elif state is ConnectionState.NO_TLS:
                yield from self.process_relay(event)
            elif state is ConnectionState.ESTABLISHED:
                yield from self.process_relay(event)
            else:
                raise RuntimeError("Unexpected state")
        else:
            yield from self.event_to_child(event)

    def process_wait_for_clienthello(self, event: events.DataReceived):
        client = self.context.client
        server = self.context.server
        # We are not ready to process this yet.
        self.recv_buffer[event.connection].extend(event.data)

        if event.connection == client and self.parse_client_hello():
            self._debug("SNI", self.client_hello.sni)
            if self.context.server.sni is True:
                self.context.server.sni = self.client_hello.sni.encode("idna")

            client_tls_requires_server_connection = (
                self.context.server.tls and
                self.context.options.upstream_cert and
                (
                    self.context.options.add_upstream_certs_to_client_chain or
                    self.client_hello.alpn_protocols or
                    not self.client_hello.sni
                )
            )

            if client_tls_requires_server_connection and not self.context.server.connected:
                yield commands.OpenConnection(self.context.server)

            if not self.context.server.connected:
                # We are only in the WAIT_FOR_CLIENTHELLO branch if we have two TLS conns.
                assert self.context.server.tls
                self.state[server] = ConnectionState.WAIT_FOR_OPENCONNECTION
            else:
                yield from self.start_server_tls()
            if client_tls_requires_server_connection:
                self.state[client] = ConnectionState.WAIT_FOR_SERVER_TLS
            else:
                yield from self.start_client_tls()

    def process_negotiate(self, event: events.DataReceived):
        # bio_write errors for b"", so we need to check first if we actually received something.
        if event.data:
            self.tls[event.connection].bio_write(event.data)
        try:
            self.tls[event.connection].do_handshake()
        except SSL.WantReadError:
            yield from self.tls_interact(event.connection)
        else:
            self.state[event.connection] = ConnectionState.ESTABLISHED
            event.connection.sni = self.tls[event.connection].get_servername()
            event.connection.alpn = self.tls[event.connection].get_alpn_proto_negotiated()

            # there might already be data in the OpenSSL BIO, so we need to trigger its processing.
            yield from self.process(events.DataReceived(event.connection, b""))

            if self.state[self.context.client] == ConnectionState.WAIT_FOR_SERVER_TLS:
                assert event.connection == self.context.server
                yield from self.start_client_tls()

    def process_relay(self, event: events.DataReceived):
        plaintext = yield from self.recv(event)
        if plaintext:
            evt = events.DataReceived(event.connection, plaintext)
            yield commands.Log(f"Plain{evt}")
            yield from self.event_to_child(evt)

    def start_server_tls(self):
        server = self.context.server

        ssl_context = SSL.Context(SSL.SSLv23_METHOD)
        self.tls[server] = SSL.Connection(ssl_context)

        if server.sni:
            self.tls[server].set_tlsext_host_name(server.sni)
        # FIXME: Handle ALPN
        self.tls[server].set_connect_state()

        self.state[server] = ConnectionState.NEGOTIATING
        yield from self.process(events.DataReceived(
            server, bytes(self.recv_buffer[server])
        ))
        self.recv_buffer[server] = bytearray()

    def start_client_tls(self):
        # FIXME
        client = self.context.client
        context = SSL.Context(SSL.SSLv23_METHOD)
        cert, privkey, cert_chain = CertStore.from_store(
            os.path.expanduser("~/.mitmproxy"), "mitmproxy"
        ).get_cert(b"example.com", (b"example.com",))
        context.use_privatekey(privkey)
        context.use_certificate(cert.x509)
        context.set_cipher_list(tls.DEFAULT_CLIENT_CIPHERS)
        self.tls[client] = SSL.Connection(context)
        self.tls[client].set_accept_state()

        self.state[client] = ConnectionState.NEGOTIATING
        yield from self.process(events.DataReceived(
            client, bytes(self.recv_buffer[client])
        ))
        self.recv_buffer[client] = bytearray()

    def tls_interact(self, conn: context.Connection):
        while True:
            try:
                data = self.tls[conn].bio_read(65535)
            except SSL.WantReadError:
                # Okay, nothing more waiting to be sent.
                return
            else:
                yield commands.SendData(conn, data)
