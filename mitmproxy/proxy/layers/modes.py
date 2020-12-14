from abc import ABCMeta

from mitmproxy import platform
from mitmproxy.net import server_spec
from mitmproxy.proxy import commands, events, layer
from mitmproxy.proxy.layers import tls
from mitmproxy.proxy.utils import expect


class HttpProxy(layer.Layer):
    @expect(events.Start)
    def _handle_event(self, event: events.Event) -> layer.CommandGenerator[None]:
        child_layer = layer.NextLayer(self.context)
        self._handle_event = child_layer.handle_event
        yield from child_layer.handle_event(event)


class DestinationKnown(layer.Layer, metaclass=ABCMeta):
    child_layer: layer.Layer

    def finish_start(self):
        if self.context.options.connection_strategy == "eager":
            err = yield commands.OpenConnection(self.context.server)
            if err:
                yield commands.CloseConnection(self.context.client)
                self._handle_event = self.done
                return

        self._handle_event = self.child_layer.handle_event
        yield from self.child_layer.handle_event(events.Start())

    @expect(events.DataReceived, events.ConnectionClosed)
    def done(self, _) -> layer.CommandGenerator[None]:
        yield from ()


class ReverseProxy(DestinationKnown):
    @expect(events.Start)
    def _handle_event(self, event: events.Event) -> layer.CommandGenerator[None]:
        spec = server_spec.parse_with_mode(self.context.options.mode)[1]
        self.context.server.address = spec.address

        if spec.scheme not in ("http", "tcp"):
            if not self.context.options.keep_host_header:
                self.context.server.sni = spec.address[0].encode()
            self.child_layer = tls.ServerTLSLayer(self.context)
        else:
            self.child_layer = layer.NextLayer(self.context)

        yield from self.finish_start()


class TransparentProxy(DestinationKnown):
    @expect(events.Start)
    def _handle_event(self, event: events.Event) -> layer.CommandGenerator[None]:
        assert platform.original_addr is not None
        socket = yield commands.GetSocket(self.context.client)
        try:
            self.context.server.address = platform.original_addr(socket)
        except Exception as e:
            yield commands.Log(f"Transparent mode failure: {e!r}")

        self.child_layer = layer.NextLayer(self.context)

        yield from self.finish_start()
