from dataclasses import dataclass

from mitmproxy import tls, connection
from mitmproxy.proxy import layer, commands, events, context
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


@dataclass
class DtlsStartServerHook(StartHook):
    """
    DTLS negotation between mitmproxy and a server is about to start.

    An addon is expected to initialize data.ssl_conn.
    (by default, this is done by `mitmproxy.addons.tlsconfig`)
    """

    data: tls.DtlsData


class _DTLSLayer(proxy_tls.TLSLayer):
    def start_handshake(self) -> layer.CommandGenerator[None]:
        yield from self.start_tls()
        if self.tls:
            yield from self.receive_handshake_data(b"")

    def start_tls(self) -> layer.CommandGenerator[None]:
        assert not self.tls

        dtls_start = tls.DtlsData(self.conn, self.context)
        if self.conn == self.context.client:
            yield DtlsStartClientHook(dtls_start)
        else:
            yield DtlsStartServerHook(dtls_start)

        if not dtls_start.ssl_conn:
            yield commands.Log(
                "No DTLS context was provided, failing connection.", "error"
            )
            yield commands.CloseConnection(self.conn)
            return
        assert dtls_start.ssl_conn
        self.tls = dtls_start.ssl_conn


class ClientDTLSLayer(_DTLSLayer):
    def __init__(self, context: context.Context):
        super().__init__(context, context.client)

    def event_to_child(self, event: events.Event) -> layer.CommandGenerator[None]:
        # start connection with server
        if self.child_layer.context.server.state is connection.ConnectionState.CLOSED:
            yield commands.OpenConnection(self.child_layer.context.server)
        yield from super().event_to_child(event)


class ServerDTLSLayer(_DTLSLayer):
    def __init__(self, context: context.Context):
        super().__init__(context, context.server)

    def event_to_child(self, event: events.Event) -> layer.CommandGenerator[None]:
        yield from ()
