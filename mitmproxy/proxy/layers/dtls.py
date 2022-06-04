from dataclasses import dataclass

from mitmproxy import tls
from mitmproxy.proxy import layer, commands, events
from mitmproxy.proxy.commands import StartHook
from mitmproxy.proxy.layers import tls as proxy_tls


@dataclass
class DtlsStartClientHook(StartHook):
    """
    DTLS negotation between mitmproxy and a client is about to start.

    An addon is expected to initialize data.ssl_conn.
    (by default, this is done by `mitmproxy.addons.tlsconfig`)
    """

    data: tls.DtlsData


class _DTLSLayer(proxy_tls._TLSLayer):
    def start_handshake(self) -> layer.CommandGenerator[None]:
        yield from self.start_tls()
        if self.tls:
            yield from self.receive_handshake_data(b"")

    def start_tls(self) -> layer.CommandGenerator[None]:
        assert not self.tls

        tls_start = tls.DtlsData(self.conn, self.context)
        if self.conn == self.context.client:
            yield DtlsStartClientHook(tls_start)

        if not tls_start.ssl_conn:
            yield commands.Log(
                "No TLS context was provided, failing connection.", "error"
            )
            yield commands.CloseConnection(self.conn)
            return
        assert tls_start.ssl_conn
        self.tls = tls_start.ssl_conn

    def event_to_child(self, event: events.Event) -> layer.CommandGenerator[None]:
        yield from ()


