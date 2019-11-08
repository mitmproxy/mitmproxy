from mitmproxy import platform
from mitmproxy.net import server_spec
from mitmproxy.proxy2 import commands, events, layer
from mitmproxy.proxy2.context import Server
from mitmproxy.proxy2.utils import expect


class ReverseProxy(layer.Layer):
    @expect(events.Start)
    def _handle_event(self, event: events.Event) -> commands.TCommandGenerator:
        spec = server_spec.parse_with_mode(self.context.options.mode)[1]
        self.context.server = Server(spec.address)
        if spec.scheme not in ("http", "tcp"):
            self.context.server.tls = True
            if not self.context.options.keep_host_header:
                self.context.server.sni = spec.address[0]
        child_layer = layer.NextLayer(self.context)
        self._handle_event = child_layer.handle_event
        yield from child_layer.handle_event(event)


class HttpProxy(layer.Layer):
    @expect(events.Start)
    def _handle_event(self, event: events.Event) -> commands.TCommandGenerator:
        child_layer = layer.NextLayer(self.context)
        self._handle_event = child_layer.handle_event
        yield from child_layer.handle_event(event)


class TransparentProxy(layer.Layer):
    @expect(events.Start)
    def _handle_event(self, event: events.Event) -> commands.TCommandGenerator:
        socket = yield commands.GetSocket(self.context.client)
        try:
            self.context.server.address = platform.original_addr(socket)
        except Exception as e:
            yield commands.Log(f"Transparent mode failure: {e!r}")

        child_layer = layer.NextLayer(self.context)
        self._handle_event = child_layer.handle_event
        yield from child_layer.handle_event(event)
