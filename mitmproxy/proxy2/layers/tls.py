import os
import struct
from typing import Any, Dict, Generator, Iterator, Optional, Tuple

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
    tls: Dict[context.Connection, SSL.Connection]
    child_layer: layer.Layer

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
        except SSL.ZeroReturnError as e:
            return False, repr(e)
        else:
            conn.tls_established = True
            conn.alpn = self.tls[conn].get_alpn_proto_negotiated()
            yield commands.Log(f"TLS established: {conn}")
            yield from self.receive(conn, b"")
            # TODO: Set all other connection attributes here
            # there might already be data in the OpenSSL BIO, so we need to trigger its processing.
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
        elif (
                isinstance(event, events.ConnectionClosed) and
                event.connection in self.tls and
                self.tls[event.connection].get_shutdown() & SSL.RECEIVED_SHUTDOWN
        ):
            pass  # We have already dispatched a ConnectionClosed to the child layer.
        else:
            yield from self.event_to_child(event)


class ServerTLSLayer(_TLSLayer):
    """
    This layer manages TLS for  potentially multiple server connections.
    """
    command_to_reply_to: Dict[context.Connection, EstablishServerTLS]

    def __init__(self, context: context.Context):
        super().__init__(context)
        self.command_to_reply_to = {}
        self.child_layer = layer.NextLayer(self.context)

    def negotiate(self, conn: context.Connection, data: bytes) -> Generator[
        commands.Command, Any, Tuple[bool, Optional[str]]]:
        done, err = yield from super().negotiate(conn, data)
        if done or err:
            cmd = self.command_to_reply_to.pop(conn)
            yield from self.event_to_child(EstablishServerTLSReply(cmd, err))
        return done, err

    def event_to_child(self, event: events.Event) -> commands.TCommandGenerator:
        for command in super().event_to_child(event):
            if isinstance(command, EstablishServerTLS):
                self.command_to_reply_to[command.connection] = command
                yield from self.start_server_tls(command.connection)
            else:
                yield command

    def start_server_tls(self, conn: context.Server):
        assert conn not in self.tls
        assert conn.connected

        ssl_context = SSL.Context(SSL.SSLv23_METHOD)
        if conn.alpn_offers:
            ssl_context.set_alpn_protos(conn.alpn_offers)
        self.tls[conn] = SSL.Connection(ssl_context)

        if conn.sni:
            if conn.sni is True:
                if self.context.client.sni:
                    conn.sni = self.context.client.sni
                else:
                    conn.sni = conn.address[0].encode()
            self.tls[conn].set_tlsext_host_name(conn.sni)
        self.tls[conn].set_connect_state()

        yield from self.negotiate(conn, b"")


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
                raise NotImplementedError from e  # TODO

            if client_hello:
                yield commands.Log(f"Client Hello: {client_hello}")

                # TODO: Don't do double conversion
                client.sni = client_hello.sni.encode("idna")
                client.alpn_offers = client_hello.alpn_protocols

                client_tls_requires_server_connection = (
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
                        yield commands.Log("Unable to establish TLS connection with server. "
                                           "Trying to establish TLS with client anyway.")

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
                    f"Cannot establish server connection: {err}"
                )
                return err

        server.alpn_offers = [
            x for x in self.context.client.alpn_offers
            if not (x.startswith(b"h2-") or x.startswith(b"spdy"))
        ]

        err = yield EstablishServerTLS(server)
        if err:
            yield commands.Log(
                f"Cannot establish TLS with server: {err}"
            )
            return err

    def start_client_tls(self) -> commands.TCommandGenerator:
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

        self.tls[client] = SSL.Connection(context)
        self.tls[client].set_accept_state()

        yield from self.negotiate(client, bytes(self.recv_buffer))
        self.recv_buffer.clear()

    def negotiate(self, conn: context.Connection, data: bytes) -> Generator[commands.Command, Any, bool]:
        done, err = yield from super().negotiate(conn, data)
        if err:
            yield commands.Log(
                f"Client TLS Handshake failed. "
                f"The client may not trust the proxy's certificate (SNI: {self.context.client.sni}).",
                level="warn"
                # TODO: Also use other sources than SNI
            )
            yield commands.CloseConnection(self.context.client)
        return done
