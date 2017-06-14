from mitmproxy.proxy.protocol2.commands import TCommandGenerator
from mitmproxy.proxy.protocol2.context import ClientServerContext, Context, Server
from mitmproxy.proxy.protocol2.events import Event
from mitmproxy.proxy.protocol2.layer import Layer
from mitmproxy.proxy.protocol2.tls import TLSLayer


class ReverseProxy(Layer):
    def __init__(self, context: Context, server_addr):
        super().__init__(context)
        server = Server(server_addr)
        self.child_context = ClientServerContext(context.client, server)
        self.child_layer = TLSLayer(self.child_context, True, True)
        # self.child_layer = TCPLayer(self.child_context)

    def handle(self, event: Event) -> TCommandGenerator:
        yield from self.child_layer.handle_event(event)
