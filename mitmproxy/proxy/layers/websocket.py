import time
from dataclasses import dataclass
from typing import Iterator, List

import wsproto
import wsproto.extensions
import wsproto.frame_protocol
import wsproto.utilities
from mitmproxy import connection, http, websocket
from mitmproxy.proxy import commands, events, layer
from mitmproxy.proxy.commands import StartHook
from mitmproxy.proxy.context import Context
from mitmproxy.proxy.events import MessageInjected
from mitmproxy.proxy.utils import expect
from wsproto import ConnectionState
from wsproto.frame_protocol import Opcode


@dataclass
class WebsocketStartHook(StartHook):
    """
    A WebSocket connection has commenced.
    """
    flow: http.HTTPFlow


@dataclass
class WebsocketMessageHook(StartHook):
    """
    Called when a WebSocket message is received from the client or
    server. The most recent message will be flow.messages[-1]. The
    message is user-modifiable. Currently there are two types of
    messages, corresponding to the BINARY and TEXT frame types.
    """
    flow: http.HTTPFlow


@dataclass
class WebsocketEndHook(StartHook):
    """
    A WebSocket connection has ended.
    You can check `flow.websocket.close_code` to determine why it ended.
    """

    flow: http.HTTPFlow


class WebSocketMessageInjected(MessageInjected[websocket.WebSocketMessage]):
    """
    The user has injected a custom WebSocket message.
    """


class WebsocketConnection(wsproto.Connection):
    """
    A very thin wrapper around wsproto.Connection:

     - we keep the underlying connection as an attribute for easy access.
     - we add a framebuffer for incomplete messages
     - we wrap .send() so that we can directly yield it.
    """
    conn: connection.Connection
    frame_buf: List[bytes]

    def __init__(self, *args, conn: connection.Connection, **kwargs):
        super(WebsocketConnection, self).__init__(*args, **kwargs)
        self.conn = conn
        self.frame_buf = [b""]

    def send2(self, event: wsproto.events.Event) -> commands.SendData:
        data = self.send(event)
        return commands.SendData(self.conn, data)

    def __repr__(self):
        return f"WebsocketConnection<{self.state.name}, {self.conn}>"


class WebsocketLayer(layer.Layer):
    """
    WebSocket layer that intercepts and relays messages.
    """
    flow: http.HTTPFlow
    client_ws: WebsocketConnection
    server_ws: WebsocketConnection

    def __init__(self, context: Context, flow: http.HTTPFlow):
        super().__init__(context)
        self.flow = flow
        assert context.server.connected

    @expect(events.Start)
    def start(self, _) -> layer.CommandGenerator[None]:

        client_extensions = []
        server_extensions = []

        # Parse extension headers. We only support deflate at the moment and ignore everything else.
        assert self.flow.response  # satisfy type checker
        ext_header = self.flow.response.headers.get("Sec-WebSocket-Extensions", "")
        if ext_header:
            for ext in wsproto.utilities.split_comma_header(ext_header.encode("ascii", "replace")):
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

    @expect(events.DataReceived, events.ConnectionClosed, WebSocketMessageInjected)
    def relay_messages(self, event: events.Event) -> layer.CommandGenerator[None]:
        assert self.flow.websocket  # satisfy type checker

        if isinstance(event, events.ConnectionEvent):
            from_client = event.connection == self.context.client
        elif isinstance(event, WebSocketMessageInjected):
            from_client = event.message.from_client
        else:
            raise AssertionError(f"Unexpected event: {event}")

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
            src_ws.receive_data(None)
        elif isinstance(event, WebSocketMessageInjected):
            fragmentizer = Fragmentizer([], event.message.type == Opcode.TEXT)
            src_ws._events.extend(
                fragmentizer(event.message.content)
            )
        else:  # pragma: no cover
            raise AssertionError(f"Unexpected event: {event}")

        for ws_event in src_ws.events():
            if isinstance(ws_event, wsproto.events.Message):
                is_text = isinstance(ws_event.data, str)
                if is_text:
                    typ = Opcode.TEXT
                    src_ws.frame_buf[-1] += ws_event.data.encode()
                else:
                    typ = Opcode.BINARY
                    src_ws.frame_buf[-1] += ws_event.data

                if ws_event.message_finished:
                    content = b"".join(src_ws.frame_buf)

                    fragmentizer = Fragmentizer(src_ws.frame_buf, is_text)
                    src_ws.frame_buf = [b""]

                    message = websocket.WebSocketMessage(typ, from_client, content)
                    self.flow.websocket.messages.append(message)
                    yield WebsocketMessageHook(self.flow)

                    if not message.dropped:
                        for msg in fragmentizer(message.content):
                            yield dst_ws.send2(msg)

                elif ws_event.frame_finished:
                    src_ws.frame_buf.append(b"")

            elif isinstance(ws_event, (wsproto.events.Ping, wsproto.events.Pong)):
                yield commands.Log(
                    f"Received WebSocket {ws_event.__class__.__name__.lower()} from {from_str} "
                    f"(payload: {bytes(ws_event.payload)!r})"
                )
                yield dst_ws.send2(ws_event)
            elif isinstance(ws_event, wsproto.events.CloseConnection):
                self.flow.websocket.timestamp_end = time.time()
                self.flow.websocket.closed_by_client = from_client
                self.flow.websocket.close_code = ws_event.code
                self.flow.websocket.close_reason = ws_event.reason

                for ws in [self.server_ws, self.client_ws]:
                    if ws.state in {ConnectionState.OPEN, ConnectionState.REMOTE_CLOSING}:
                        # response == original event, so no need to differentiate here.
                        yield ws.send2(ws_event)
                    yield commands.CloseConnection(ws.conn)
                yield WebsocketEndHook(self.flow)
                self._handle_event = self.done
            else:  # pragma: no cover
                raise AssertionError(f"Unexpected WebSocket event: {ws_event}")

    @expect(events.DataReceived, events.ConnectionClosed, WebSocketMessageInjected)
    def done(self, _) -> layer.CommandGenerator[None]:
        yield from ()


class Fragmentizer:
    """
    Theory (RFC 6455):
       Unless specified otherwise by an extension, frames have no semantic
       meaning.  An intermediary might coalesce and/or split frames, [...]

    Practice:
        Some WebSocket servers reject large payload sizes.
        Other WebSocket servers reject CONTINUATION frames.

    As a workaround, we either retain the original chunking or, if the payload has been modified, use ~4kB chunks.
    If one deals with web servers that do not support CONTINUATION frames, addons need to monkeypatch FRAGMENT_SIZE
    if they need to modify the message.
    """
    # A bit less than 4kb to accommodate for headers.
    FRAGMENT_SIZE = 4000

    def __init__(self, fragments: List[bytes], is_text: bool):
        self.fragment_lengths = [len(x) for x in fragments]
        self.is_text = is_text

    def msg(self, data: bytes, message_finished: bool):
        if self.is_text:
            data_str = data.decode(errors="replace")
            return wsproto.events.TextMessage(data_str, message_finished=message_finished)
        else:
            return wsproto.events.BytesMessage(data, message_finished=message_finished)

    def __call__(self, content: bytes) -> Iterator[wsproto.events.Message]:
        if len(content) == sum(self.fragment_lengths):
            # message has the same length, we can reuse the same sizes
            offset = 0
            for fl in self.fragment_lengths[:-1]:
                yield self.msg(content[offset:offset + fl], False)
                offset += fl
            yield self.msg(content[offset:], True)
        else:
            offset = 0
            total = len(content) - self.FRAGMENT_SIZE
            while offset < total:
                yield self.msg(content[offset:offset + self.FRAGMENT_SIZE], False)
                offset += self.FRAGMENT_SIZE
            yield self.msg(content[offset:], True)
