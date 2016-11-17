from mitmproxy.proxy.protocol2 import events
from mitmproxy.proxy.protocol2.context import ClientServerContext
from mitmproxy.proxy.protocol2.events import TEventGenerator
from mitmproxy.proxy.protocol2.layer import Layer


class TCPLayer(Layer):
    context = None  # type: ClientServerContext

    def handle_event(self, event: events.Event) -> TEventGenerator:
        if isinstance(event, events.Start):
            if not self.context.server.connected:
                try:
                    t = yield events.OpenConnection(self.context.server)
                    yield
                    print("opening took {}s".format(t))  # example on how we can implement .ask()
                except Exception as e:
                    print("Could not connect to server: {}".format(e))

        if isinstance(event, events.ReceiveData):
            if event.connection == self.context.client:
                dst = self.context.server
            else:
                dst = self.context.client
            yield events.SendData(dst, event.data)
