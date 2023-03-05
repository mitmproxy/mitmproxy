import time
from enum import auto
from enum import Enum
from typing import Union

from mitmproxy import connection
from mitmproxy.proxy import commands
from mitmproxy.proxy import context
from mitmproxy.proxy import events
from mitmproxy.proxy import layer
from mitmproxy.proxy.layer import Layer


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
    tunnel_connection: connection.Connection
    """The 'outer' connection which provides the tunnel protocol I/O"""
    conn: connection.Connection
    """The 'inner' connection which provides data I/O"""
    tunnel_state: TunnelState = TunnelState.INACTIVE
    command_to_reply_to: commands.OpenConnection | None = None
    _event_queue: list[events.Event]
    """
    If the connection already exists when we receive the start event,
    we buffer commands until we have established the tunnel.
    """

    def __init__(
        self,
        context: context.Context,
        tunnel_connection: connection.Connection,
        conn: connection.Connection,
    ):
        super().__init__(context)
        self.tunnel_connection = tunnel_connection
        self.conn = conn
        self.child_layer = layer.NextLayer(self.context)
        self._event_queue = []

    def __repr__(self):
        return f"{type(self).__name__}({self.tunnel_state.name.lower()})"

    def _handle_event(self, event: events.Event) -> layer.CommandGenerator[None]:
        if isinstance(event, events.Start):
            if self.tunnel_connection.state is not connection.ConnectionState.CLOSED:
                # we might be in the interesting state here where the connection is already half-closed,
                # for example because next_layer buffered events and the client disconnected in the meantime.
                # we still expect a close event to arrive, so we carry on here as normal for now.
                self.tunnel_state = TunnelState.ESTABLISHING
                yield from self.start_handshake()
            yield from self.event_to_child(event)
        elif (
            isinstance(event, events.ConnectionEvent)
            and event.connection == self.tunnel_connection
        ):
            if isinstance(event, events.DataReceived):
                if self.tunnel_state is TunnelState.ESTABLISHING:
                    done, err = yield from self.receive_handshake_data(event.data)
                    if done:
                        if self.conn != self.tunnel_connection:
                            self.conn.state = connection.ConnectionState.OPEN
                            self.conn.timestamp_start = time.time()
                    if err:
                        if self.conn != self.tunnel_connection:
                            self.conn.state = connection.ConnectionState.CLOSED
                            self.conn.timestamp_start = time.time()
                        yield from self.on_handshake_error(err)
                    if done or err:
                        yield from self._handshake_finished(err)
                else:
                    yield from self.receive_data(event.data)
            elif isinstance(event, events.ConnectionClosed):
                if self.conn != self.tunnel_connection:
                    self.conn.state &= ~connection.ConnectionState.CAN_READ
                    self.conn.timestamp_end = time.time()
                if self.tunnel_state is TunnelState.OPEN:
                    yield from self.receive_close()
                elif self.tunnel_state is TunnelState.ESTABLISHING:
                    err = "connection closed"
                    yield from self.on_handshake_error(err)
                    yield from self._handshake_finished(err)
                self.tunnel_state = TunnelState.CLOSED
            else:  # pragma: no cover
                raise AssertionError(f"Unexpected event: {event}")
        else:
            yield from self.event_to_child(event)

    def _handshake_finished(self, err: str | None) -> layer.CommandGenerator[None]:
        if err:
            self.tunnel_state = TunnelState.CLOSED
        else:
            self.tunnel_state = TunnelState.OPEN
        if self.command_to_reply_to:
            yield from self.event_to_child(
                events.OpenConnectionCompleted(self.command_to_reply_to, err)
            )
            self.command_to_reply_to = None
        else:
            for evt in self._event_queue:
                yield from self.event_to_child(evt)
            self._event_queue.clear()

    def _handle_command(
        self, command: commands.Command
    ) -> layer.CommandGenerator[None]:
        if (
            isinstance(command, commands.ConnectionCommand)
            and command.connection == self.conn
        ):
            if isinstance(command, commands.SendData):
                yield from self.send_data(command.data)
            elif isinstance(command, commands.CloseConnection):
                if self.conn != self.tunnel_connection:
                    self.conn.state &= ~connection.ConnectionState.CAN_WRITE
                    command.connection = self.tunnel_connection
                yield from self.send_close(command)
            elif isinstance(command, commands.OpenConnection):
                # create our own OpenConnection command object that blocks here.
                self.command_to_reply_to = command
                self.tunnel_state = TunnelState.ESTABLISHING
                err = yield commands.OpenConnection(self.tunnel_connection)
                if err:
                    yield from self.event_to_child(
                        events.OpenConnectionCompleted(command, err)
                    )
                    self.tunnel_state = TunnelState.CLOSED
                else:
                    yield from self.start_handshake()
            else:  # pragma: no cover
                raise AssertionError(f"Unexpected command: {command}")
        else:
            yield command

    def event_to_child(self, event: events.Event) -> layer.CommandGenerator[None]:
        if (
            self.tunnel_state is TunnelState.ESTABLISHING
            and not self.command_to_reply_to
        ):
            self._event_queue.append(event)
            return
        for command in self.child_layer.handle_event(event):
            yield from self._handle_command(command)

    def start_handshake(self) -> layer.CommandGenerator[None]:
        yield from self._handle_event(events.DataReceived(self.tunnel_connection, b""))

    def receive_handshake_data(
        self, data: bytes
    ) -> layer.CommandGenerator[tuple[bool, str | None]]:
        """returns a (done, err) tuple"""
        yield from ()
        return True, None

    def on_handshake_error(self, err: str) -> layer.CommandGenerator[None]:
        """Called if either receive_handshake_data returns an error or we receive a close during handshake."""
        yield commands.CloseConnection(self.tunnel_connection)

    def receive_data(self, data: bytes) -> layer.CommandGenerator[None]:
        yield from self.event_to_child(events.DataReceived(self.conn, data))

    def receive_close(self) -> layer.CommandGenerator[None]:
        yield from self.event_to_child(events.ConnectionClosed(self.conn))

    def send_data(self, data: bytes) -> layer.CommandGenerator[None]:
        yield commands.SendData(self.tunnel_connection, data)

    def send_close(
        self, command: commands.CloseConnection
    ) -> layer.CommandGenerator[None]:
        yield command


class LayerStack:
    def __init__(self) -> None:
        self._stack: list[Layer] = []

    def __getitem__(self, item: int) -> Layer:
        return self._stack.__getitem__(item)

    def __truediv__(self, other: Union[Layer, "LayerStack"]) -> "LayerStack":
        if isinstance(other, Layer):
            if self._stack:
                self._stack[-1].child_layer = other  # type: ignore
            self._stack.append(other)
        else:
            if self._stack:
                self._stack[-1].child_layer = other[0]  # type: ignore
            self._stack.extend(other._stack)
        return self
