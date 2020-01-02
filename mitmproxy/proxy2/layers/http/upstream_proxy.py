from enum import Enum, auto
from typing import Optional, Tuple

from h11._receivebuffer import ReceiveBuffer

from mitmproxy import http
from mitmproxy.net.http import http1
from mitmproxy.net.http.http1 import read_sansio as http1_sansio
from mitmproxy.proxy2 import commands, context, events, layer
from mitmproxy.utils import human


class TunnelState(Enum):
    INACTIVE = auto()
    ESTABLISHING = auto()
    OPEN = auto()
    CLOSED = auto()


class TunnelLayer(layer.Layer):
    child_layer: layer.Layer
    tunnel_connection: context.Connection
    original_destination: context.Connection
    tunnel_state: TunnelState = TunnelState.INACTIVE
    command_to_reply_to: Optional[commands.OpenConnection] = None

    def __init__(
            self,
            context: context.Context,
            tunnel_connection: Optional[context.Connection] = None,
            original_destination: Optional[context.Connection] = None,
    ):
        super().__init__(context)
        self.tunnel_connection = tunnel_connection or context.server
        self.original_destination = original_destination or context.server
        self.child_layer = layer.NextLayer(self.context)

    def _handle_event(self, event: events.Event) -> layer.CommandGenerator[None]:
        if isinstance(event, events.ConnectionEvent) and event.connection == self.tunnel_connection:
            if isinstance(event, events.DataReceived):
                if self.tunnel_state is TunnelState.ESTABLISHING:
                    done, err = yield from self.receive_handshake_data(event)
                    if done:
                        self.tunnel_state = TunnelState.OPEN
                    if err:
                        yield commands.CloseConnection(self.tunnel_connection)
                        self.tunnel_state = TunnelState.CLOSED
                        yield from self.on_handshake_error(err)
                    if (done or err) and self.command_to_reply_to:
                        yield from self.event_to_child(events.OpenConnectionReply(self.command_to_reply_to, err))
                        self.command_to_reply_to = None
                else:
                    yield from self.receive_data(event.data)
            elif isinstance(event, events.ConnectionClosed):
                if self.tunnel_state is TunnelState.OPEN:
                    yield from self.receive_close()
                elif self.tunnel_state is TunnelState.ESTABLISHING:
                    yield from self.on_handshake_error("connection closed without notice")
            else:
                raise NotImplementedError(f"Unexpected event: {event}")
        else:
            yield from self.event_to_child(event)

    def event_to_child(self, event: events.Event) -> layer.CommandGenerator[None]:
        for command in self.child_layer.handle_event(event):
            if isinstance(command, commands.ConnectionCommand) and command.connection == self.original_destination:
                if isinstance(command, commands.SendData):
                    yield from self.send_data(command.data)
                elif isinstance(command, commands.CloseConnection):
                    yield from self.send_close()
                elif isinstance(command, commands.OpenConnection):
                    # create our own OpenConnection command object that blocks here.
                    self.tunnel_state = TunnelState.ESTABLISHING
                    err = yield commands.OpenConnection(self.tunnel_connection)
                    if err:
                        yield from self.event_to_child(events.OpenConnectionReply(command, err))
                    else:
                        self.original_destination.state = self.tunnel_connection.state
                        self.command_to_reply_to = command
                        yield from self.start_handshake()
                else:
                    raise NotImplementedError(f"Unexpected command: {command}")
            else:
                yield command

    def start_handshake(self) -> layer.CommandGenerator[None]:
        yield from self._handle_event(events.DataReceived(self.tunnel_connection, b""))

    def receive_handshake_data(self, event: events.DataReceived) -> layer.CommandGenerator[Tuple[bool, Optional[str]]]:
        yield from ()
        return True, None

    def on_handshake_error(self, err: str) -> layer.CommandGenerator[None]:
        """Called if either receive_handshake_data returns an error or we receive a close during handshake."""
        yield commands.CloseConnection(self.tunnel_connection)

    def receive_data(self, data: bytes) -> layer.CommandGenerator[None]:
        yield from self.event_to_child(
            events.DataReceived(self.original_destination, data)
        )

    def receive_close(self) -> layer.CommandGenerator[None]:
        self.original_destination.state &= self.tunnel_connection.state
        yield from self.event_to_child(
            events.ConnectionClosed(self.original_destination)
        )

    def send_data(self, data: bytes) -> layer.CommandGenerator[None]:
        yield commands.SendData(self.tunnel_connection, data)

    def send_close(self) -> layer.CommandGenerator[None]:
        yield commands.CloseConnection(self.tunnel_connection)



class TunnelStack:
    def __init__(self):
        self._stack = []

    def __getitem__(self, item):
        return self._stack.__getitem__(item)

    def __truediv__(self, other):
        if self._stack:
            self._stack[-1].child_layer = other
        self._stack.append(other)
        return self


class HttpUpstreamProxy(TunnelLayer):
    buf: ReceiveBuffer

    def __init__(self, ctx: context.Context, address: tuple):
        s = context.Server(address)
        ctx.server.via = (*ctx.server.via, s)
        super().__init__(ctx, tunnel_connection=s)
        self.buf = ReceiveBuffer()

    def start_handshake(self) -> layer.CommandGenerator[None]:
        req = http.make_connect_request(self.original_destination.address)
        raw = http1.assemble_request(req)
        yield commands.SendData(self.tunnel_connection, raw)

    def receive_handshake_data(self, event: events.DataReceived) -> layer.CommandGenerator[Tuple[bool, Optional[str]]]:
        self.buf += event.data
        response_head = self.buf.maybe_extract_lines()
        if response_head:
            response_head = [bytes(x) for x in response_head]  # TODO: Make url.parse compatible with bytearrays
            try:
                response = http.HTTPResponse.wrap(http1_sansio.read_response_head(response_head))
            except ValueError as e:
                yield commands.Log(f"{human.format_address(self.tunnel_connection.address)}: {e}")
                return False, str(e)
            if 200 <= response.status_code < 300:
                if self.buf:
                    yield from self.receive_data(bytes(self.buf))
                    del self.buf
                return True, None
            else:
                raw_resp = b"\n".join(response_head)
                yield commands.Log(f"{human.format_address(self.tunnel_connection.address)}: {raw_resp}", level="debug")
                return False, f"{response.status_code} {response.reason}"
        else:
            return False, None
