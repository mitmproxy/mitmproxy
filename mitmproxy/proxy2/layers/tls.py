import os
import struct
from enum import Enum
from typing import MutableMapping, Generator, Optional, Iterable, Iterator

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
    NEGOTIATING = 5
    ESTABLISHED = 6


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
        N:   NEGOTIATING
        E:   ESTABLISHED

    +------------+          +---+                             +------------+
    |Client State|--------> | / |                             |Server State|
    +------------+ no tls   +---+                server tls,  +------------+   server tls,
      |                                          client tls       | | |       no client tls
      v client tls                              +-----------------+ | +--------------------+
                                                |                   |                      |
      +------------------------------+          |                   | no server tls        |
      |  no server tls               |          v                   v                      v
      |                              v                                   OpenConn(TLS)
      v server tls                            +---+  not needed   +--------------------> +---+
                             +---> +---+      |WCH+-------------> | / |                  | N | <-+
    +---+                    |     | N |      +---+               +---+ <--------------------+   |
    |WCH|                    |  +> +---+        |                       OpenConn(No TLS)   |     |
    +---+                    |  |    |          |                   ^                      |     |
      |                      |  |    v          | already connec-   |       handshake done v     |
      |ClientHello arrives   |  |  +---+        | ted or server     |                            |
      |                      |  |  | E |        | info needed       |   OpenConn(No TLS) +---+   |
      +----------------------+  |  +---+        |                   +--------------------+ E |   |
      |  no server info needed  |               |                                        +---+   |
      |                         |               |                                                |
      v server info needed      |               +------------------------------------------------+
                                |
    +---+                       |
    |WST|-----------------------+
    +---+  server tls established
           (or errored)
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
            yield commands.Log(f"Plain{send_command}")
            self.tls[send_command.connection].sendall(send_command.data)
            yield from self.tls_interact(send_command.connection)

    def event_to_child(self, event: events.Event) -> commands.TCommandGenerator:
        for command in self.child_layer.handle_event(event):
            if isinstance(command, commands.SendData):
                yield from self.send(command)
            elif isinstance(command, commands.OpenConnection):
                raise NotImplementedError()
            else:
                yield command

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
                yield from self.event_to_child(event)
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
                self.state[server] = ConnectionState.NO_TLS
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
        if event.data:
            self.tls[event.connection].bio_write(event.data)
        yield from self.tls_interact(event.connection)

        plaintext = bytearray()
        while True:
            try:
                plaintext.extend(self.tls[event.connection].recv(65535))
            except (SSL.WantReadError, SSL.ZeroReturnError):
                break

        if plaintext:
            evt = events.DataReceived(event.connection, bytes(plaintext))
            yield commands.Log(f"Plain{evt}")
            yield from self.event_to_child(evt)

    def start_server_tls(self):
        server = self.context.server

        ssl_context = SSL.Context(SSL.SSLv23_METHOD)
        self.tls[server] = SSL.Connection(ssl_context)

        if server.sni:
            if server.sni is True:
                if self.client_hello:
                    server.sni = self.client_hello.sni.encode("idna")
                else:
                    server.sni = server.address[0].encode("idna")
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
