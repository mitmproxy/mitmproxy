from dataclasses import dataclass

from mitmproxy import flow
from mitmproxy import udp
from mitmproxy.connection import Connection
from mitmproxy.proxy import commands
from mitmproxy.proxy import events
from mitmproxy.proxy import layer
from mitmproxy.proxy.commands import StartHook
from mitmproxy.proxy.context import Context
from mitmproxy.proxy.events import MessageInjected
from mitmproxy.proxy.utils import expect


@dataclass
class UdpStartHook(StartHook):
    """
    A UDP connection has started.
    """

    flow: udp.UDPFlow


@dataclass
class UdpMessageHook(StartHook):
    """
    A UDP connection has received a message. The most recent message
    will be flow.messages[-1]. The message is user-modifiable.
    """

    flow: udp.UDPFlow


@dataclass
class UdpEndHook(StartHook):
    """
    A UDP connection has ended.
    """

    flow: udp.UDPFlow


@dataclass
class UdpErrorHook(StartHook):
    """
    A UDP error has occurred.

    Every UDP flow will receive either a udp_error or a udp_end event, but not both.
    """

    flow: udp.UDPFlow


class UdpMessageInjected(MessageInjected[udp.UDPMessage]):
    """
    The user has injected a custom UDP message.
    """


class UDPLayer(layer.Layer):
    """
    Simple UDP layer that just relays messages right now.
    """

    flow: udp.UDPFlow | None

    def __init__(self, context: Context, ignore: bool = False):
        super().__init__(context)
        if ignore:
            self.flow = None
        else:
            self.flow = udp.UDPFlow(self.context.client, self.context.server, True)

    @expect(events.Start)
    def start(self, _) -> layer.CommandGenerator[None]:
        if self.flow:
            yield UdpStartHook(self.flow)

        if self.context.server.timestamp_start is None:
            err = yield commands.OpenConnection(self.context.server)
            if err:
                if self.flow:
                    self.flow.error = flow.Error(str(err))
                    yield UdpErrorHook(self.flow)
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
        yield commands.CloseConnection(self.context.server)
        yield commands.CloseConnection(self.context.client)
        yield UdpErrorHook(self.flow)
        self.flow.live = False

    @expect(
        events.DataReceived,
        events.ConnectionClosed,
        UdpMessageInjected,
        events.KillInjected,
    )
    def relay_messages(self, event: events.Event) -> layer.CommandGenerator[None]:
        if isinstance(event, events.KillInjected):
            if self.flow and event.flow is self.flow:
                yield from self._kill()
            return

        if isinstance(event, UdpMessageInjected):
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
                udp_message = udp.UDPMessage(from_client, event.data)
                self.flow.messages.append(udp_message)
                yield UdpMessageHook(self.flow)
                # An addon may have called flow.kill() inside the hook.
                # Flow.kill() injects KillInjected asynchronously, so it has
                # not reached us yet; check synchronously here so a killed
                # flow's in-flight datagram is not forwarded (#8200).
                if self._killed():
                    yield from self._kill()
                    return
                yield commands.SendData(send_to, udp_message.content)
            else:
                yield commands.SendData(send_to, event.data)

        elif isinstance(event, events.ConnectionClosed):
            self._handle_event = self.done
            yield commands.CloseConnection(send_to)
            if self.flow:
                yield UdpEndHook(self.flow)
                self.flow.live = False
        else:
            raise AssertionError(f"Unexpected event: {event}")

    @expect(
        events.DataReceived,
        events.ConnectionClosed,
        UdpMessageInjected,
        events.KillInjected,
    )
    def done(self, _) -> layer.CommandGenerator[None]:
        yield from ()
