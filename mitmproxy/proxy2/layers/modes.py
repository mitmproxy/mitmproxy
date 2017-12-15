from mitmproxy.net import server_spec
from mitmproxy.proxy2 import layer
from mitmproxy.proxy2.context import Context, Server


class ReverseProxy(layer.Layer):
    def __init__(self, context: Context):
        super().__init__(context)
        spec = server_spec.parse_with_mode(context.options.mode)[1]
        self.context.server = Server(spec.address)
        if spec.scheme != "http":
            self.context.server.tls = True
            if not context.options.keep_host_header:
                self.context.server.sni = spec.address[0]
        child_layer = layer.NextLayer(self.context)
        self._handle_event = child_layer.handle_event


class HttpProxy(layer.Layer):
    def __init__(self, context: Context):
        super().__init__(context)
        child_layer = layer.NextLayer(self.context)
        self._handle_event = child_layer.handle_event
