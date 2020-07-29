from enum import Enum, auto
from typing import Optional, Tuple

from mitmproxy.proxy2 import commands, context, events, layer


class TunnelState(Enum):
    INACTIVE = auto()
    ESTABLISHING = auto()
    OPEN = auto()
    CLOSED = auto()


class TunnelLayer(layer.Layer):
    """
    A specialized layer that simplifies the implementation of tunneling protocols such as SOCKS, upstream HTTP proxies,
    or TLS.
    """
    child_layer: layer.Layer
    tunnel_connection: context.Connection
    """The 'outer' connection which provides the tunnel protocol I/O"""
    conn: context.Connection
    """The 'inner' connection which provides data I/O"""
    tunnel_state: TunnelState = TunnelState.INACTIVE
    command_to_reply_to: Optional[commands.OpenConnection] = None

    def __init__(
            self,
            context: context.Context,
            tunnel_connection: context.Connection,
            conn: context.Connection,
    ):
        super().__init__(context)
        self.tunnel_connection = tunnel_connection
        self.conn = conn
        self.child_layer = layer.NextLayer(self.context)

    def __repr__(self):
        return f"{type(self).__name__}({self.tunnel_state.name.lower()})"

    def _handle_event(self, event: events.Event) -> layer.CommandGenerator[None]:
        if isinstance(event, events.Start):
            if self.tunnel_connection.connected:
                self.tunnel_state = TunnelState.ESTABLISHING
                yield from self.start_handshake()
            yield from self.event_to_child(event)
        elif isinstance(event, events.ConnectionEvent) and event.connection == self.tunnel_connection:
            if isinstance(event, events.DataReceived):
                if self.tunnel_state is TunnelState.ESTABLISHING:
                    done, err = yield from self.receive_handshake_data(event.data)
                    if done:
                        if self.conn != self.tunnel_connection:
                            self.conn.state = context.ConnectionState.OPEN
                        self.tunnel_state = TunnelState.OPEN
                    if err:
                        self.tunnel_state = TunnelState.CLOSED
                        yield from self.on_handshake_error(err)
                    if (done or err) and self.command_to_reply_to:
                        yield from self.event_to_child(events.OpenConnectionReply(self.command_to_reply_to, err))
                        self.command_to_reply_to = None
                else:
                    yield from self.receive_data(event.data)
            elif isinstance(event, events.ConnectionClosed):
                if self.conn != self.tunnel_connection:
                    self.conn.state &= ~context.ConnectionState.CAN_READ
                if self.tunnel_state is TunnelState.OPEN:
                    yield from self.receive_close()
                elif self.tunnel_state is TunnelState.ESTABLISHING:
                    yield from self.on_handshake_error("connection closed without notice")
            else:
                raise AssertionError(f"Unexpected event: {event}")
        else:
            yield from self.event_to_child(event)

    def event_to_child(self, event: events.Event) -> layer.CommandGenerator[None]:
        for command in self.child_layer.handle_event(event):
            if isinstance(command, commands.ConnectionCommand) and command.connection == self.conn:
                if isinstance(command, commands.SendData):
                    yield from self.send_data(command.data)
                elif isinstance(command, commands.CloseConnection):
                    if self.conn != self.tunnel_connection:
                        self.conn.state &= ~context.ConnectionState.CAN_WRITE
                    yield from self.send_close()
                elif isinstance(command, commands.OpenConnection):
                    # create our own OpenConnection command object that blocks here.
                    self.tunnel_state = TunnelState.ESTABLISHING
                    err = yield commands.OpenConnection(self.tunnel_connection)
                    if err:
                        yield from self.event_to_child(events.OpenConnectionReply(command, err))
                    else:
                        self.command_to_reply_to = command
                        yield from self.start_handshake()
                else:
                    raise AssertionError(f"Unexpected command: {command}")
            else:
                yield command

    def start_handshake(self) -> layer.CommandGenerator[None]:
        yield from self._handle_event(events.DataReceived(self.tunnel_connection, b""))

    def receive_handshake_data(self, data: bytes) -> layer.CommandGenerator[Tuple[bool, Optional[str]]]:
        yield from ()
        return True, None

    def on_handshake_error(self, err: str) -> layer.CommandGenerator[None]:
        """Called if either receive_handshake_data returns an error or we receive a close during handshake."""
        yield commands.CloseConnection(self.tunnel_connection)

    def receive_data(self, data: bytes) -> layer.CommandGenerator[None]:
        yield from self.event_to_child(
            events.DataReceived(self.conn, data)
        )

    def receive_close(self) -> layer.CommandGenerator[None]:
        yield from self.event_to_child(
            events.ConnectionClosed(self.conn)
        )

    def send_data(self, data: bytes) -> layer.CommandGenerator[None]:
        yield commands.SendData(self.tunnel_connection, data)

    def send_close(self) -> layer.CommandGenerator[None]:
        yield commands.CloseConnection(self.tunnel_connection)


class LayerStack:
    def __init__(self):
        self._stack = []

    def __getitem__(self, item):
        return self._stack.__getitem__(item)

    def __truediv__(self, other):
        if self._stack:
            self._stack[-1].child_layer = other
        self._stack.append(other)
        return self


class OpenConnectionStub(layer.Layer):
    done = False
    err = None

    def _handle_event(self, event: events.Event) -> layer.CommandGenerator[None]:
        if isinstance(event, events.Start):
            self.err = yield commands.OpenConnection(self.context.server)
            self.done = not self.err
        else:
            self.err = event
