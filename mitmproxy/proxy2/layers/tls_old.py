"""
TLS man-in-the-middle layer.
"""
# We may want to split this up into client (only once) and server (for every server) layer.
import os
from typing import MutableMapping
from warnings import warn

from OpenSSL import SSL

from mitmproxy.certs import CertStore
from mitmproxy.proxy.protocol.tls import DEFAULT_CLIENT_CIPHERS
from mitmproxy.proxy2 import events, commands, layer
from mitmproxy.proxy2.context import Context, Connection
from mitmproxy.proxy2.utils import expect


class TLSLayer(layer.Layer):
    client_tls: bool  # FIXME: not yet used.
    server_tls: bool
    child_layer: layer.Layer = None
    tls: MutableMapping[Connection, SSL.Connection]

    def __init__(self, context: Context, client_tls: bool, server_tls: bool):
        super().__init__(context)
        self.state = self.start
        self.client_tls = client_tls
        self.server_tls = server_tls
        self.tls = {}

    def _handle_event(self, event: events.Event) -> commands.TCommandGenerator:
        yield from self.state(event)

    @expect(events.Start)
    def start(self, _) -> commands.TCommandGenerator:
        yield from self.start_client_tls()
        if not self.context.server.connected:
            # TODO: This should be lazy.
            yield commands.OpenConnection(self.context.server)
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
                yield commands.SendData(conn, data)

    @expect(events.ConnectionClosed, events.DataReceived)
    def establish_tls(self, event: events.Event) -> commands.TCommandGenerator:
        if isinstance(event, events.DataReceived):
            self.tls[event.connection].bio_write(event.data)
            try:
                self.tls[event.connection].do_handshake()
            except SSL.WantReadError:
                pass
            yield from self.tls_interact(event.connection)

            both_handshakes_done = (
                self.tls[self.context.client].get_peer_finished() and
                self.context.server in self.tls and self.tls[
                    self.context.server].get_peer_finished()
            )

            if both_handshakes_done:
                print("both handshakes done")
                self.child_layer = layer.NextLayer(self.context)
                yield from self.child_layer.handle_event(events.Start())
                self.state = self.relay_messages
                yield from self.state(events.DataReceived(self.context.server, b""))
                yield from self.state(events.DataReceived(self.context.client, b""))

        elif isinstance(event, events.ConnectionClosed):
            warn("unimplemented: tls.establish_tls:close")

    @expect(events.ConnectionClosed, events.DataReceived)
    def relay_messages(self, event: events.Event) -> commands.TCommandGenerator:
        if isinstance(event, events.DataReceived):
            if event.data:
                self.tls[event.connection].bio_write(event.data)
                yield from self.tls_interact(event.connection)

            while True:
                try:
                    plaintext = self.tls[event.connection].recv(4096)
                except (SSL.WantReadError, SSL.ZeroReturnError):
                    return

                event_for_child = events.DataReceived(self.context.server, plaintext)

                for event_from_child in self.child_layer.handle_event(event_for_child):
                    if isinstance(event_from_child, commands.SendData):
                        self.tls[event_from_child.connection].sendall(event_from_child.data)
                        yield from self.tls_interact(event_from_child.connection)
                    else:
                        yield event_from_child
        elif isinstance(event, events.ConnectionClosed):
            warn("unimplemented: tls.relay_messages:close")
