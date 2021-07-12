from dataclasses import dataclass
from typing import Optional

from mitmproxy import flow, tcp
from mitmproxy.proxy import commands, events, layer
from mitmproxy.proxy.commands import StartHook
from mitmproxy.connection import ConnectionState, Connection
from mitmproxy.proxy.context import Context
from mitmproxy.proxy.events import MessageInjected
from mitmproxy.proxy.utils import expect


@dataclass
class TcpStartHook(StartHook):
    """
    A TCP connection has started.
    """

    flow: tcp.TCPFlow


@dataclass
class TcpMessageHook(StartHook):
    """
    A TCP connection has received a message. The most recent message
    will be flow.messages[-1]. The message is user-modifiable.
    """
    flow: tcp.TCPFlow


@dataclass
class TcpEndHook(StartHook):
    """
    A TCP connection has ended.
    """
    flow: tcp.TCPFlow


@dataclass
class TcpErrorHook(StartHook):
    """
    A TCP error has occurred.

    Every TCP flow will receive either a tcp_error or a tcp_end event, but not both.
    """
    flow: tcp.TCPFlow


class TcpMessageInjected(MessageInjected[tcp.TCPMessage]):
    """
    The user has injected a custom TCP message.
    """


class TCPLayer(layer.Layer):
    """
    Simple TCP layer that just relays messages right now.
    """
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

        if self.context.server.timestamp_start is None:
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

    @expect(events.DataReceived, events.ConnectionClosed, TcpMessageInjected)
    def relay_messages(self, event: events.Event) -> layer.CommandGenerator[None]:

        if isinstance(event, TcpMessageInjected):
            # we just spoof that we received data here and then process that regularly.
            event = events.DataReceived(
                self.context.client if event.message.from_client else self.context.server,
                event.message.content,
            )

        assert isinstance(event, events.ConnectionEvent)

        from_client = event.connection == self.context.client
        send_to: Connection
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
        else:
            raise AssertionError(f"Unexpected event: {event}")

    @expect(events.DataReceived, events.ConnectionClosed, TcpMessageInjected)
    def done(self, _) -> layer.CommandGenerator[None]:
        yield from ()
