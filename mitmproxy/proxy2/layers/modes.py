from mitmproxy.net import server_spec
from mitmproxy.proxy2 import layer
from mitmproxy.proxy2.context import Context, Server


class ReverseProxy(layer.Layer):
    def __init__(self, context: Context):
        super().__init__(context)
        server_addr = server_spec.parse_with_mode(context.options.mode)[1].address
        self.context.server = Server(server_addr)

        child_layer = layer.NextLayer(self.context)
        self._handle_event = child_layer.handle_event
