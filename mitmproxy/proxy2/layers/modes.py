from mitmproxy.proxy2 import events
from mitmproxy.proxy2.commands import TCommandGenerator
from mitmproxy.proxy2.context import Context, Server, ClientServerContext
from mitmproxy.proxy2.layer import Layer
from mitmproxy.proxy2.layers.http import HTTPLayer


class ReverseProxy(Layer):
    def __init__(self, context: Context, server_addr):
        super().__init__(context)
        server = Server(server_addr)
        self.child_context = ClientServerContext(context.client, server)
        # self.child_layer = TLSLayer(self.child_context, True, True)
        # self.child_layer = TCPLayer(self.child_context, False)
        self.child_layer = HTTPLayer(self.child_context)

    def _handle_event(self, event: events.Event) -> TCommandGenerator:
        yield from self.child_layer.handle_event(event)
