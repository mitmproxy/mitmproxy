from mitmproxy import http, flow
from mitmproxy.proxy2 import events, commands
from mitmproxy.proxy2.context import Context
from mitmproxy.proxy2.layer import Layer
from mitmproxy.proxy2.utils import expect


class HTTP2Layer(Layer):
    context: Context = None
    flow: websocket.WebSocketFlow

    def __init__(self, context: Context):
        super().__init__(context)
        print("HERE")
        assert context.server.connected

    @expect(events.Start)
    def start(self, _) -> commands.TCommandGenerator:
        pass

    @expect(events.DataReceived, events.ConnectionClosed)
    def done(self, _):
        yield from ()

    _handle_event = start
