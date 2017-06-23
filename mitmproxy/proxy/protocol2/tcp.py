import typing
from warnings import warn

from mitmproxy.proxy.protocol2 import events, commands
from mitmproxy.proxy.protocol2.context import ClientServerContext
from mitmproxy.proxy.protocol2.layer import Layer
from mitmproxy.proxy.protocol2.utils import expect


class TCPLayer(Layer):
    """
    Simple TCP layer that just relays messages right now.
    """
    context: ClientServerContext = None

    # this is like a mini state machine.
    state: typing.Callable[[events.Event], commands.TCommandGenerator]

    def __init__(self, context: ClientServerContext):
        super().__init__(context)
        self.state = self.start

    def handle(self, event: events.Event) -> commands.TCommandGenerator:
        yield from self.state(event)

    @expect(events.Start)
    def start(self, _) -> commands.TCommandGenerator:
        if not self.context.server.connected:
            ok = yield commands.OpenConnection(self.context.server)
        self.state = self.relay_messages

    @expect(events.DataReceived, events.ConnectionClosed)
    def relay_messages(self, event: events.Event) -> commands.TCommandGenerator:
        if isinstance(event, events.ClientDataReceived):
            yield commands.SendData(self.context.server, event.data)

        elif isinstance(event, events.ServerDataReceived):
            yield commands.SendData(self.context.client, event.data)

        elif isinstance(event, events.ConnectionClosed):
            warn("unimplemented: tcp.relay_message:close")
            # TODO: close other connection here.
