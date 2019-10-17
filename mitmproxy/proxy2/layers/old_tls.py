
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
    This layer manages TLS for a single server connection.
    """
    lazy_init: bool = False

    def __init__(self, context: context.Context):
        super().__init__(context)
        self.child_layer = layer.NextLayer(context)

    @expect(events.Start)
    def start(self, event: events.Start) -> commands.TCommandGenerator:
        yield from self.child_layer.handle_event(event)

        server = self.context.server
        if server.tls:
            if server.connected:
                yield from self._start_tls(server)
            else:
                self.lazy_init = True
        self._handle_event = self.process

    _handle_event = start

    def process(self, event: events.Event) -> None:
        if isinstance(event, events.DataReceived) and event.connection in self.tls:
            if not event.connection.tls_established:
                yield from self.negotiate(event)
            else:
                yield from self.relay(event)
        elif isinstance(event, events.OpenConnectionReply):
            err = event.reply
            conn = event.command.connection
            if self.lazy_init and not err and conn == self.context.server:
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
                    server.sni = self.context.client.sni
                else:
                    server.sni = server.address[0]
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
                if client_tls_requires_server_connection and not server.tls_established:
                    yield from self.start_server_tls()
                    self._handle_event = self.state_wait_for_server_tls
                else:
                    yield from self.start_negotiate()
                    self._handle_event = self.state_process

                # In any case, we now have enough information to start server TLS if needed.
                yield from self.child_layer.handle_event(events.Start())
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
            if not self.context.client.tls_established:
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
            self.context.server.alpn_offers = [
                x for x in self.context.client.alpn_offers
                if not (x.startswith(b"h2-") or x.startswith(b"spdy"))
            ]

            err = yield commands.OpenConnection(self.context.server)
            if err:
                yield commands.Log(
                    "Cannot establish server connection, which is required to establish TLS with the client."
                )

    def start_negotiate(self):
        # FIXME: Do this properly
        client = self.context.client
        server = self.context.server
        context = SSL.Context(SSL.SSLv23_METHOD)
        cert, privkey, cert_chain = CertStore.from_store(
            os.path.expanduser("~/.mitmproxy"), "mitmproxy",
            self.context.options.key_size
        ).get_cert(client.sni.encode(), (client.sni.encode(),))
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
                # We probably need better checks when negotiating with the client.
                return options[0]

        context.set_alpn_select_callback(alpn_select_callback)

        self.tls[self.context.client] = SSL.Connection(context)
        self.tls[self.context.client].set_accept_state()

        yield from self.state_process(events.DataReceived(
            client, bytes(self.recv_buffer)
        ))
        self.recv_buffer = bytearray()
