from dataclasses import dataclass

from mitmproxy import flow
from mitmproxy import tcp
from mitmproxy.connection import Connection
from mitmproxy.connection import ConnectionState
from mitmproxy.proxy import commands
from mitmproxy.proxy import events
from mitmproxy.proxy import layer
from mitmproxy.proxy.commands import StartHook
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

    flow: tcp.TCPFlow | None

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

    def _killed(self) -> bool:
        """True if Flow.kill() has marked this flow as killed."""
        return bool(
            self.flow
            and self.flow.error
            and self.flow.error.msg == flow.Error.KILLED_MESSAGE
        )

    def _kill(self) -> layer.CommandGenerator[None]:
        """Close both connections and emit the error hook for a killed flow."""
        assert self.flow
        self._handle_event = self.done
        if self.context.server.state is not ConnectionState.CLOSED:
            yield commands.CloseConnection(self.context.server)
        if self.context.client.state is not ConnectionState.CLOSED:
            yield commands.CloseConnection(self.context.client)
        yield TcpErrorHook(self.flow)
        self.flow.live = False

    @expect(
        events.DataReceived,
        events.ConnectionClosed,
        TcpMessageInjected,
        events.KillInjected,
    )
    def relay_messages(self, event: events.Event) -> layer.CommandGenerator[None]:
        if isinstance(event, events.KillInjected):
            if self.flow and event.flow is self.flow:
                yield from self._kill()
            return

        if isinstance(event, TcpMessageInjected):
            # we just spoof that we received data here and then process that regularly.
            event = events.DataReceived(
                self.context.client
                if event.message.from_client
                else self.context.server,
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
                # An addon may have called flow.kill() inside the hook.
                # Flow.kill() injects KillInjected asynchronously, so it has
                # not reached us yet; check synchronously here so a killed
                # flow's in-flight message is not forwarded (#8200).
                if self._killed():
                    yield from self._kill()
                    return
                yield commands.SendData(send_to, tcp_message.content)
            else:
                yield commands.SendData(send_to, event.data)

        elif isinstance(event, events.ConnectionClosed):
            all_done = not (
                (self.context.client.state & ConnectionState.CAN_READ)
                or (self.context.server.state & ConnectionState.CAN_READ)
            )
            if all_done:
                self._handle_event = self.done
                if self.context.server.state is not ConnectionState.CLOSED:
                    yield commands.CloseConnection(self.context.server)
                if self.context.client.state is not ConnectionState.CLOSED:
                    yield commands.CloseConnection(self.context.client)
                if self.flow:
                    yield TcpEndHook(self.flow)
                    self.flow.live = False
            else:
                yield commands.CloseTcpConnection(send_to, half_close=True)
        else:
            raise AssertionError(f"Unexpected event: {event}")

    @expect(
        events.DataReceived,
        events.ConnectionClosed,
        TcpMessageInjected,
        events.KillInjected,
    )
    def done(self, _) -> layer.CommandGenerator[None]:
        yield from ()
