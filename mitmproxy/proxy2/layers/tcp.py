from mitmproxy import tcp, flow
from mitmproxy.proxy2 import commands, events
from mitmproxy.proxy2.context import Context
from mitmproxy.proxy2.layer import Layer
from mitmproxy.proxy2.utils import expect


class TCPLayer(Layer):
    """
    Simple TCP layer that just relays messages right now.
    """
    context: Context
    ignore: bool
    flow: tcp.TCPFlow

    def __init__(self, context: Context, ignore: bool = False):
        super().__init__(context)
        self.ignore = ignore
        self.flow = None

    @expect(events.Start)
    def start(self, _) -> commands.TCommandGenerator:
        if not self.ignore:
            self.flow = tcp.TCPFlow(self.context.client, self.context.server, True)
            yield commands.Hook("tcp_start", self.flow)

        if not self.context.server.connected:
            try:
                yield commands.OpenConnection(self.context.server)
            except IOError as e:
                if not self.ignore:
                    self.flow.error = flow.Error(str(e))
                    yield commands.Hook("tcp_error", self.flow)
                yield commands.CloseConnection(self.context.client)
                self._handle_event = self.done
                return
        self._handle_event = self.relay_messages

    _handle_event = start

    @expect(events.DataReceived, events.ConnectionClosed)
    def relay_messages(self, event: events.ConnectionEvent) -> commands.TCommandGenerator:
        from_client = event.connection == self.context.client
        if from_client:
            send_to = self.context.server
        else:
            send_to = self.context.client

        if isinstance(event, events.DataReceived):
            if self.ignore:
                yield commands.SendData(send_to, event.data)
            else:
                tcp_message = tcp.TCPMessage(from_client, event.data)
                self.flow.messages.append(tcp_message)
                yield commands.Hook("tcp_message", self.flow)
                yield commands.SendData(send_to, tcp_message.content)

        elif isinstance(event, events.ConnectionClosed):
            yield commands.CloseConnection(send_to)
            if not self.ignore:
                yield commands.Hook("tcp_end", self.flow)
            self._handle_event = self.done

    @expect(events.DataReceived, events.ConnectionClosed)
    def done(self, _):
        yield from ()
