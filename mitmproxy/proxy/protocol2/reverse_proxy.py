from mitmproxy.proxy.protocol2.context import ClientServerContext, Context, Server
from mitmproxy.proxy.protocol2.events import Event, TEventGenerator
from mitmproxy.proxy.protocol2.layer import Layer
from mitmproxy.proxy.protocol2.tls import TLSLayer


class ReverseProxy(Layer):
    def __init__(self, context: Context, server_addr):
        super().__init__(context)
        server = Server(server_addr)
        self.child_context = ClientServerContext(context.client, server)
        self.child_layer = TLSLayer(self.child_context, True, True)

    def handle_event(self, event: Event) -> TEventGenerator:
        yield from self.child_layer.handle_event(event)

        # If we cannot use yield from, we have to use something like this:
        # x = None
        # evts = self.child_layer.handle_event(event)
        # while True:
        #     x = yield evts.send(x)
        # https://www.python.org/dev/peps/pep-0380/#formal-semantics
        # This is obviously ugly - but do we have any cases where we need to intercept messages like this?
