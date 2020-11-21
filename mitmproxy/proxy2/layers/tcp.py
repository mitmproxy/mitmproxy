from typing import Optional

from mitmproxy import flow, tcp
from mitmproxy.proxy2 import commands, events, layer
from mitmproxy.proxy2.commands import Hook
from mitmproxy.proxy2.context import ConnectionState, Context
from mitmproxy.proxy2.utils import expect


class TcpStartHook(Hook):
    flow: tcp.TCPFlow


class TcpMessageHook(Hook):
    flow: tcp.TCPFlow


class TcpEndHook(Hook):
    flow: tcp.TCPFlow


class TcpErrorHook(Hook):
    flow: tcp.TCPFlow


class TCPLayer(layer.Layer):
    """
    Simple TCP layer that just relays messages right now.
    """
    context: Context
    flow: Optional[tcp.TCPFlow]

    def __init__(self, context: Context, ignore: bool = False):
        super().__init__(context)
        if ignore:
            self.flow = None
        else:
            self.flow = tcp.TCPFlow(self.context.client, self.context.server, True)

    @expect(events.Start)
    def start(self, _) -> layer.CommandGenerator[None]:
        if self.flow:
            yield TcpStartHook(self.flow)

        if not self.context.server.connected:
            err = yield commands.OpenConnection(self.context.server)
            if err:
                if self.flow:
                    self.flow.error = flow.Error(str(err))
                    yield TcpErrorHook(self.flow)
                yield commands.CloseConnection(self.context.client)
                self._handle_event = self.done
                return
        self._handle_event = self.relay_messages

    _handle_event = start

    @expect(events.DataReceived, events.ConnectionClosed)
    def relay_messages(self, event: events.ConnectionEvent) -> layer.CommandGenerator[None]:
        from_client = event.connection == self.context.client
        if from_client:
            send_to = self.context.server
        else:
            send_to = self.context.client

        if isinstance(event, events.DataReceived):
            if self.flow:
                tcp_message = tcp.TCPMessage(from_client, event.data)
                self.flow.messages.append(tcp_message)
                yield TcpMessageHook(self.flow)
                yield commands.SendData(send_to, tcp_message.content)
            else:
                yield commands.SendData(send_to, event.data)

        elif isinstance(event, events.ConnectionClosed):
            all_done = not (
                    (self.context.client.state & ConnectionState.CAN_READ)
                    or
                    (self.context.server.state & ConnectionState.CAN_READ)
            )
            if all_done:
                if self.context.server.state is not ConnectionState.CLOSED:
                    yield commands.CloseConnection(self.context.server)
                if self.context.client.state is not ConnectionState.CLOSED:
                    yield commands.CloseConnection(self.context.client)
                self._handle_event = self.done
                if self.flow:
                    yield TcpEndHook(self.flow)
            else:
                yield commands.CloseConnection(send_to, half_close=True)

    @expect(events.DataReceived, events.ConnectionClosed)
    def done(self, _) -> layer.CommandGenerator[None]:
        yield from ()
