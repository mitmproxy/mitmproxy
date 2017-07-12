from mitmproxy import websocket, http
from mitmproxy.proxy.protocol2 import events, commands
from mitmproxy.proxy.protocol2.context import ClientServerContext
from mitmproxy.proxy.protocol2.layer import Layer
from mitmproxy.proxy.protocol2.utils import expect


class WebsocketLayer(Layer):
    """
    Simple TCP layer that just relays messages right now.
    """
    context: ClientServerContext = None
    flow: websocket.WebSocketFlow

    def __init__(self, context: ClientServerContext, handshake_flow: http.HTTPFlow):
        super().__init__(context)
        self.flow = websocket.WebSocketFlow(context.client, context.server, handshake_flow)
        assert context.server.connected

    @expect(events.Start)
    def start(self, _) -> commands.TCommandGenerator:
        yield from ()
        self._handle_event = self.relay_messages

    @expect(events.DataReceived, events.ConnectionClosed)
    def relay_messages(self, event: events.Event) -> commands.TCommandGenerator:
        raise NotImplementedError()

    _handle_event = start
