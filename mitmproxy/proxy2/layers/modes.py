from mitmproxy.proxy2 import events
from mitmproxy.proxy2.commands import TCommandGenerator
from mitmproxy.proxy2.context import Context, Server
from mitmproxy.proxy2.layer import Layer
from mitmproxy.proxy2.layers.http import HTTPLayer


class ReverseProxy(Layer):
    def __init__(self, context: Context, server_addr):
        super().__init__(context)
        self.context.server = Server(server_addr)
        # self.child_layer = TLSLayer(self.context, True, True)
        # self.child_layer = TCPLayer(self.context, False)
        self.child_layer = HTTPLayer(self.context)

    def _handle_event(self, event: events.Event) -> TCommandGenerator:
        yield from self.child_layer.handle_event(event)
