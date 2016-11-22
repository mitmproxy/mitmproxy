import functools
from warnings import warn

from mitmproxy.proxy.protocol2 import events
from mitmproxy.proxy.protocol2.context import ClientServerContext
from mitmproxy.proxy.protocol2.events import TEventGenerator
from mitmproxy.proxy.protocol2.layer import Layer
from mitmproxy.proxy.protocol2.utils import defer, only
from mitmproxy.proxy.protocol2.utils import exit_on_close


class TCPLayer(Layer):
    context = None  # type: ClientServerContext

    def __init__(self, context: ClientServerContext):
        super().__init__(context)
        self.state = self.start

    def handle_event(self, event: events.Event) -> TEventGenerator:
        yield from self.state(event)

    @only(events.Start)
    def start(self, _) -> TEventGenerator:
        if not self.context.server.connected:
            yield events.OpenConnection(self.context.server)
            self.state = self.wait_for_open
        else:
            self.state = self.relay_messages

    @defer(events.ReceiveData)
    @exit_on_close
    @only(events.OpenConnection)
    def wait_for_open(self, _) -> TEventGenerator:
        self.state = self.relay_messages
        yield from []

    @only(events.ReceiveData, events.CloseConnection)
    def relay_messages(self, event: events.Event) -> TEventGenerator:
        if isinstance(event, events.ReceiveClientData):
            yield events.SendData(self.context.server, event.data)
        elif isinstance(event, events.ReceiveServerData):
            yield events.SendData(self.context.client, event.data)
        elif isinstance(event, events.CloseConnection):
            warn("unimplemented: tcp.relay_message:close")
            # TODO: close other connection here.
