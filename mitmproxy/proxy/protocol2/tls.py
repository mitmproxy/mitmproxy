import os
from typing import MutableMapping
from warnings import warn

from OpenSSL import SSL
from mitmproxy.certs import CertStore
from mitmproxy.options import DEFAULT_CLIENT_CIPHERS
from mitmproxy.proxy.protocol2 import events
from mitmproxy.proxy.protocol2.context import ClientServerContext, Connection
from mitmproxy.proxy.protocol2.events import TEventGenerator
from mitmproxy.proxy.protocol2.layer import Layer
from mitmproxy.proxy.protocol2.tcp import TCPLayer
from mitmproxy.proxy.protocol2.utils import only, defer


class TLSLayer(Layer):
    context = None  # type: ClientServerContext
    client_tls = None  # type: bool
    server_tls = None  # type: bool
    # client_data = None  # type: Buffer
    # server_data = None  # type: Buffer
    child_layer = None  # type: Layer

    def __init__(self, context: ClientServerContext, client_tls: bool, server_tls: bool):
        super().__init__(context)
        self.state = self.start
        self.client_tls = client_tls
        self.server_tls = server_tls
        # self.client_data = Buffer()
        # self.server_data = Buffer()
        self.tls = {}  # type: MutableMapping[Connection, SSL.Connection]

    def handle_event(self, event: events.Event) -> TEventGenerator:
        yield from self.state(event)

    @only(events.Start)
    def start(self, _) -> TEventGenerator:
        yield from self.start_client_tls()
        if not self.context.server.connected:
            yield events.OpenConnection(self.context.server)
        else:
            yield from self.start_server_tls()
        self.state = self.establish_tls

    def start_client_tls(self):
        conn = self.context.client
        context = SSL.Context(SSL.SSLv23_METHOD)
        cert, privkey, cert_chain = CertStore.from_store(
            os.path.expanduser("~/.mitmproxy"), "mitmproxy"
        ).get_cert(b"example.com", (b"example.com",))
        context.use_privatekey(privkey)
        context.use_certificate(cert.x509)
        context.set_cipher_list(DEFAULT_CLIENT_CIPHERS)
        self.tls[conn] = SSL.Connection(context)
        self.tls[conn].set_accept_state()
        try:
            self.tls[conn].do_handshake()
        except SSL.WantReadError:
            pass
        yield from self.tls_interact(conn)

    def start_server_tls(self):
        conn = self.context.server
        self.tls[conn] = SSL.Connection(SSL.Context(SSL.SSLv23_METHOD))
        self.tls[conn].set_connect_state()
        try:
            self.tls[conn].do_handshake()
        except SSL.WantReadError:
            pass
        yield from self.tls_interact(conn)

    def tls_interact(self, conn: Connection):
        while True:
            try:
                data = self.tls[conn].bio_read(4096)
            except SSL.WantReadError:
                # Okay, nothing more waiting to be sent.
                return
            else:
                yield events.SendData(conn, data)

    @only(events.OpenConnection, events.CloseConnection, events.ReceiveData)
    def establish_tls(self, event: events.Event) -> TEventGenerator:
        if isinstance(event, events.OpenConnection):
            yield from self.start_server_tls()
        elif isinstance(event, events.ReceiveData):
            self.tls[event.connection].bio_write(event.data)
            try:
                self.tls[event.connection].do_handshake()
            except SSL.WantReadError:
                pass
            yield from self.tls_interact(event.connection)

            both_handshakes_done = (
                self.tls[self.context.client].get_peer_finished() and
                self.context.server in self.tls and self.tls[self.context.server].get_peer_finished()
            )

            if both_handshakes_done:
                print("both handshakes done")
                # FIXME: This'd be accomplised by asking the master.
                self.child_layer = TCPLayer(self.context)
                yield from self.child_layer.handle_event(events.Start())
                self.state = self.relay_messages
                yield from self.state(events.ReceiveData(self.context.server, b""))
                yield from self.state(events.ReceiveData(self.context.client, b""))




        elif isinstance(event, events.CloseConnection):
            warn("unimplemented: tls.establish_tls:close")

    @defer(events.ReceiveData, events.CloseConnection)
    def set_next_layer(self, layer):
        # FIXME: That'd be a proper event, not just the layer.
        self.child_layer = layer  # type: Layer
        self.state = self.relay_messages

    @only(events.CloseConnection, events.ReceiveData)
    def relay_messages(self, event: events.Event) -> TEventGenerator:
        if isinstance(event, events.ReceiveData):
            if event.data:
                self.tls[event.connection].bio_write(event.data)
                yield from self.tls_interact(event.connection)

            while True:
                try:
                    plaintext = self.tls[event.connection].recv(4096)
                except (SSL.WantReadError, SSL.ZeroReturnError):
                    return
                if event.connection == self.context.client:
                    event_for_child = events.ReceiveClientData(self.context.client, plaintext)
                else:
                    event_for_child = events.ReceiveServerData(self.context.server, plaintext)

                for event_from_child in self.child_layer.handle_event(event_for_child):
                    if isinstance(event_from_child, events.SendData):
                        self.tls[event_from_child.connection].sendall(event_from_child.data)
                        yield from self.tls_interact(event_from_child.connection)
                    else:
                        yield event_from_child
        elif isinstance(event, events.CloseConnection):
            warn("unimplemented: tls.relay_messages:close")
