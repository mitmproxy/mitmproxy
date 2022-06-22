import time
from typing import Optional

from mitmproxy import tls, connection
from mitmproxy.proxy import layer, commands, context, events
from mitmproxy.proxy.layers import tls as proxy_tls, udp


def start_dtls(tls_layer: proxy_tls.TLSLayer) -> layer.CommandGenerator[None]:
    assert not tls_layer.tls

    dtls_start = tls.TlsData(tls_layer.conn, tls_layer.context, is_dtls=True)
    if tls_layer.conn == tls_layer.context.client:
        yield proxy_tls.TlsStartClientHook(dtls_start)
    else:
        yield proxy_tls.TlsStartServerHook(dtls_start)

    if not dtls_start.ssl_conn:
        yield commands.Log(
            "No DTLS context was provided, failing connection.", "error"
        )
        yield commands.CloseConnection(tls_layer.conn)
        return
    assert dtls_start.ssl_conn
    tls_layer.tls = dtls_start.ssl_conn


class ClientDTLSLayer(proxy_tls.ClientTLSLayer):
    def __init__(self, context: context.Context):
        super().__init__(context)
        self.server_tls_available = isinstance(self.context.layers[-2], ServerDTLSLayer)

    start_tls = start_dtls

    def start_server_tls(self) -> layer.CommandGenerator[Optional[str]]:
        if not self.server_tls_available:
            return "No server DTLS available."
        err = yield commands.OpenConnection(self.context.server)
        return err

    def receive_handshake_data(
            self, data: bytes
    ) -> layer.CommandGenerator[tuple[bool, Optional[str]]]:
        if self.client_hello_parsed:
            return (yield from super().receive_handshake_data(data))
        self.recv_buffer.extend(data)
        try:
            client_hello = proxy_tls.parse_client_hello(self.recv_buffer, dtls=True)
        except ValueError:
            return False, f"Cannot parse ClientHello: {self.recv_buffer.hex()}"

        if client_hello:
            self.client_hello_parsed = True
        else:
            return False, None

        self.conn.sni = client_hello.sni
        self.conn.alpn_offers = client_hello.alpn_protocols
        tls_clienthello = proxy_tls.ClientHelloData(self.context, client_hello)
        yield proxy_tls.TlsClienthelloHook(tls_clienthello)

        if tls_clienthello.ignore_connection:
            # we've figured out that we don't want to intercept this connection, so we assign fake connection objects
            # to all TLS layers. This makes the real connection contents just go through.
            self.conn = self.tunnel_connection = connection.Client(
                ("ignore-conn", 0), ("ignore-conn", 0), time.time()
            )
            parent_layer = self.context.layers[self.context.layers.index(self) - 1]
            if isinstance(parent_layer, ServerDTLSLayer):
                parent_layer.conn = parent_layer.tunnel_connection = connection.Server(
                    None
                )
            self.child_layer = udp.UDPLayer(self.context)
            yield from self.event_to_child(
                events.DataReceived(self.context.client, bytes(self.recv_buffer))
            )
            self.recv_buffer.clear()
            return True, None
        if (
                tls_clienthello.establish_server_tls_first
                and not self.context.server.tls_established
        ):
            err = yield from self.start_server_tls()
            if err:
                yield commands.Log(
                    f"Unable to establish DTLS connection with server ({err}). "
                    f"Trying to establish DTLS with client anyway."
                )

        yield from self.start_tls()
        if not self.conn.connected:
            return False, "connection closed early"

        ret = yield from super().receive_handshake_data(bytes(self.recv_buffer))
        self.recv_buffer.clear()
        return ret


class ServerDTLSLayer(proxy_tls.ServerTLSLayer):
    start_tls = start_dtls
