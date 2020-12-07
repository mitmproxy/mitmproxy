from typing import Optional

import wsproto
import wsproto.utilities
import wsproto.frame_protocol
import wsproto.extensions

from mitmproxy import flow, tcp, websocket, http
from mitmproxy.proxy2 import commands, events, layer, context
from mitmproxy.proxy2.commands import Hook
from mitmproxy.proxy2.context import Context
from mitmproxy.proxy2.utils import expect


class WebsocketStartHook(Hook):
    """
    A WebSocket connection has commenced.
    """
    flow: websocket.WebSocketFlow


class WebsocketMessageHook(Hook):
    """
    Called when a WebSocket message is received from the client or
    server. The most recent message will be flow.messages[-1]. The
    message is user-modifiable. Currently there are two types of
    messages, corresponding to the BINARY and TEXT frame types.
    """
    flow: websocket.WebSocketFlow


class WebsocketEndHook(Hook):
    """
    A WebSocket connection has ended.
    """

    flow: websocket.WebSocketFlow


class WebsocketErrorHook(Hook):
    """
    A WebSocket connection has had an error.

    Every WebSocket flow will receive either a websocket_error or a websocket_end event, but not both.
    """
    flow: websocket.WebSocketFlow


class WebsocketConnection(wsproto.Connection):
    """
    A very thin wrapper around wsproto.Connection
    that just adds the underlying connection as an attribute for easy access.
    """
    conn: context.Connection

    def __init__(self, *args, conn: context.Connection, **kwargs):
        super(WebsocketConnection, self).__init__(*args, **kwargs)
        self.conn = conn


class WebsocketLayer(layer.Layer):
    """
    WebSocket layer that intercepts and relays messages.
    """
    flow: Optional[websocket.WebSocketFlow]
    client_ws: WebsocketConnection
    server_ws: WebsocketConnection

    def __init__(self, context: Context, handshake_flow: http.HTTPFlow):
        super().__init__(context)
        self.flow = websocket.WebSocketFlow(context.client, context.server, handshake_flow)
        assert context.server.connected

    @expect(events.Start)
    def start(self, _) -> layer.CommandGenerator[None]:

        client_extensions = []
        server_extensions = []

        # Parse extension headers. We only support deflate at the moment and ignore everything else.
        ext_header = self.flow.handshake_flow.response.headers.get("Sec-WebSocket-Extensions", "")
        if ext_header:
            for ext in wsproto.utilities.split_comma_header(ext_header):
                ext_name = ext.split(";", 1)[0].strip()
                if ext_name == wsproto.extensions.PerMessageDeflate.name:
                    client_deflate = wsproto.extensions.PerMessageDeflate()
                    client_deflate.finalize(ext)
                    client_extensions.append(client_deflate)
                    server_deflate = wsproto.extensions.PerMessageDeflate()
                    server_deflate.finalize(ext)
                    server_extensions.append(server_deflate)
                else:
                    yield commands.Log(f"Ignoring unknown WebSocket extension {ext_name!r}.")

        self.client_ws = WebsocketConnection(wsproto.ConnectionType.SERVER, client_extensions, conn=self.context.client)
        self.server_ws = WebsocketConnection(wsproto.ConnectionType.CLIENT, server_extensions, conn=self.context.server)

        yield WebsocketStartHook(self.flow)

        self._handle_event = self.relay_messages

    _handle_event = start

    @expect(events.DataReceived, events.ConnectionClosed)
    def relay_messages(self, event: events.ConnectionEvent) -> layer.CommandGenerator[None]:
        from_client = event.connection == self.context.client
        from_str = 'client' if from_client else 'server'
        if from_client:
            src_ws = self.client_ws
            dst_ws = self.server_ws
        else:
            src_ws = self.server_ws
            dst_ws = self.client_ws

        if isinstance(event, events.DataReceived):
            src_ws.receive_data(event.data)
        elif isinstance(event, events.ConnectionClosed):
            if src_ws.state not in {wsproto.ConnectionState.OPEN, wsproto.ConnectionState.LOCAL_CLOSING}:
                return
            src_ws.receive_data(None)
        else:
            raise AssertionError(f"Unexpected event: {event}")

        for ws_event in src_ws.events():
            if isinstance(ws_event, wsproto.events.Message):
                yield commands.SendData(dst_ws.conn, dst_ws.send(ws_event))
                yield commands.Log("WARN: LOG WS")
            elif isinstance(ws_event, (wsproto.events.Ping, wsproto.events.Pong)):
                yield commands.Log(
                    f"Received WebSocket {event.__class__.__name__.lower()} from {from_str} "
                    f"(payload: {ws_event.payload!r})"
                )
                yield commands.SendData(dst_ws.conn, dst_ws.send(ws_event))
            elif isinstance(ws_event, wsproto.events.CloseConnection):
                self.flow.close_sender = from_str
                self.flow.close_code = ws_event.code
                self.flow.close_reason = ws_event.reason

                for ws in [self.client_ws, self.server_ws]:
                    if ws.state in {wsproto.ConnectionState.OPEN, wsproto.ConnectionState.REMOTE_CLOSING}:
                        # response == original event, so no need to differentiate here.
                        yield commands.SendData(ws.conn, ws.send(ws_event))
                        yield commands.CloseConnection(ws.conn)
                if ws_event.code in {1000, 1001, 1005}:
                    yield WebsocketEndHook(self.flow)
                else:
                    self.flow.error = flow.Error(f"WebSocket Error: {format_close_event(ws_event)}")
                    yield WebsocketErrorHook(self.flow)
                yield commands.CloseConnection(self.context.client)
            else:
                raise AssertionError(f"Unexpected WebSocket event: {ws_event}")

    """
    @expect(events.DataReceived, events.ConnectionClosed)
    def done(self, _) -> layer.CommandGenerator[None]:
        yield from ()
    """


def format_close_event(event: wsproto.events.CloseConnection) -> str:
    try:
        ret = wsproto.frame_protocol.CloseReason(event.code).name
    except ValueError:
        ret = f"UNKNOWN_ERROR={event.code}"
    if event.reason:
        ret += f" (reason: {event.reason})"
    return ret
