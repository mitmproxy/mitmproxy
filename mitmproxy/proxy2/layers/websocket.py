import wsproto
from wsproto import events as wsevents
from wsproto.connection import ConnectionType, WSConnection
from wsproto.extensions import PerMessageDeflate

from mitmproxy import websocket, http, flow
from mitmproxy.proxy2 import events, commands
from mitmproxy.proxy2.context import Context
from mitmproxy.proxy2.layer import Layer
from mitmproxy.proxy2.utils import expect


class WebsocketLayer(Layer):
    """
    Simple TCP layer that just relays messages right now.
    """
    context: Context = None
    flow: websocket.WebSocketFlow

    def __init__(self, context: Context, handshake_flow: http.HTTPFlow):
        super().__init__(context)
        self.flow = websocket.WebSocketFlow(context.client, context.server, handshake_flow)
        self.flow.metadata['websocket_handshake'] = handshake_flow.id
        self.handshake_flow = handshake_flow
        self.handshake_flow.metadata['websocket_flow'] = self.flow.id
        self.client_frame_buffer = []
        self.server_frame_buffer = []

        assert context.server.connected

    @expect(events.Start)
    def start(self, _) -> commands.TCommandGenerator:
        extensions = []
        if 'Sec-WebSocket-Extensions' in self.handshake_flow.response.headers:
            if PerMessageDeflate.name in self.handshake_flow.response.headers['Sec-WebSocket-Extensions']:
                extensions = [PerMessageDeflate()]
        self.client_conn = WSConnection(ConnectionType.SERVER,
                                        extensions=extensions)
        self.server_conn = WSConnection(ConnectionType.CLIENT,
                                        host=self.handshake_flow.request.host,
                                        resource=self.handshake_flow.request.path,
                                        extensions=extensions)
        if extensions:
            self.client_conn.extensions[0].finalize(self.client_conn, self.handshake_flow.response.headers['Sec-WebSocket-Extensions'])
            self.server_conn.extensions[0].finalize(self.server_conn, self.handshake_flow.response.headers['Sec-WebSocket-Extensions'])

        data = self.server_conn.bytes_to_send()
        self.client_conn.receive_bytes(data)

        event = next(self.client_conn.events())
        assert isinstance(event, wsevents.ConnectionRequested)

        self.client_conn.accept(event)
        self.server_conn.receive_bytes(self.client_conn.bytes_to_send())
        assert isinstance(next(self.server_conn.events()), wsevents.ConnectionEstablished)

        yield commands.Hook("websocket_start", self.flow)
        self._handle_event = self.relay_messages

    _handle_event = start

    @expect(events.DataReceived, events.ConnectionClosed)
    def relay_messages(self, event: events.Event) -> commands.TCommandGenerator:
        if isinstance(event, events.DataReceived):
            from_client = event.connection == self.context.client
            if from_client:
                source = self.client_conn
                other = self.server_conn
                fb = self.client_frame_buffer
                send_to = self.context.server
            else:
                source = self.server_conn
                other = self.client_conn
                fb = self.server_frame_buffer
                send_to = self.context.client

            source.receive_bytes(event.data)

            closing = False
            received_ws_events = list(source.events())
            for ws_event in received_ws_events:
                if isinstance(ws_event, wsevents.DataReceived):
                    yield from self._handle_data_received(ws_event, source, other, send_to, from_client, fb)
                elif isinstance(ws_event, wsevents.PingReceived):
                    yield from self._handle_ping_received(ws_event, source, other, send_to, from_client)
                elif isinstance(ws_event, wsevents.PongReceived):
                    yield from self._handle_pong_received(ws_event, source, other, send_to, from_client)
                elif isinstance(ws_event, wsevents.ConnectionClosed):
                    yield from self._handle_connection_closed(ws_event, source, other, send_to, from_client)
                    closing = True
                else:
                    yield commands.Log(
                        "info",
                        "WebSocket unhandled event: from {}: {}".format("client" if from_client else "server", ws_event)
                    )

                if closing:
                    yield commands.Hook("websocket_end", self.flow)
                    if not from_client:
                        yield commands.CloseConnection(self.context.client)
                    self._handle_event = self.done

        # TODO: elif isinstance(event, events.InjectMessage):
        # TODO: come up with a solid API to inject messages

        elif isinstance(event, events.ConnectionClosed):
            yield commands.Log("error", "Connection closed abnormally")
            self.flow.error = flow.Error(
                "WebSocket connection closed unexpectedly by {}".format(
                    "client" if event.connection == self.context.client else "server"
                )
            )
            if event.connection == self.context.server:
                yield commands.CloseConnection(self.context.client)
            yield commands.Hook("websocket_error", self.flow)
            yield commands.Hook("websocket_end", self.flow)
            self._handle_event = self.done

    @expect(events.DataReceived, events.ConnectionClosed)
    def done(self, _):
        yield from ()

    def _handle_data_received(self, ws_event, source, other, send_to, from_client, fb):
        fb.append(ws_event.data)

        if ws_event.message_finished:
            original_chunk_sizes = [len(f) for f in fb]

            if isinstance(ws_event, wsevents.TextReceived):
                message_type = wsproto.frame_protocol.Opcode.TEXT
                payload = ''.join(fb)
            else:
                message_type = wsproto.frame_protocol.Opcode.BINARY
                payload = b''.join(fb)

            fb.clear()

            websocket_message = websocket.WebSocketMessage(message_type, from_client, payload)
            length = len(websocket_message.content)
            self.flow.messages.append(websocket_message)
            yield commands.Hook("websocket_message", self.flow)

            if not self.flow.stream and not websocket_message.killed:
                def get_chunk(payload):
                    if len(payload) == length:
                        # message has the same length, we can reuse the same sizes
                        pos = 0
                        for s in original_chunk_sizes:
                            yield (payload[pos:pos + s], True if pos + s == length else False)
                            pos += s
                    else:
                        # just re-chunk everything into 4kB frames
                        # header len = 4 bytes without masking key and 8 bytes with masking key
                        chunk_size = 4088 if from_client else 4092
                        chunks = range(0, len(payload), chunk_size)
                        for i in chunks:
                            yield (payload[i:i + chunk_size], True if i + chunk_size >= len(payload) else False)

                for chunk, final in get_chunk(websocket_message.content):
                    other.send_data(chunk, final)
                    yield commands.SendData(send_to, other.bytes_to_send())

        if self.flow.stream:
            other.send_data(ws_event.data, ws_event.message_finished)
            yield commands.SendData(send_to, other.bytes_to_send())

    def _handle_ping_received(self, ws_event, source, other, send_to, from_client):
        yield commands.Log(
            "info",
            "WebSocket PING received from {}: {}".format("client" if from_client else "server",
                                                         ws_event.payload.decode() or "<no payload>")
        )
        # We do not forward the PING payload, as this might leak information!
        other.ping()
        yield commands.SendData(send_to, other.bytes_to_send())
        # PING is automatically answered with a PONG by wsproto
        yield commands.SendData(self.context.client if from_client else self.context.server, source.bytes_to_send())

    def _handle_pong_received(self, ws_event, source, other, send_to, from_client):
        yield commands.Log(
            "info",
            "WebSocket PONG received from {}: {}".format("client" if from_client else "server",
                                                         ws_event.payload.decode() or "<no payload>")
        )

    def _handle_connection_closed(self, ws_event, source, other, send_to, from_client):
        self.flow.close_sender = "client" if from_client else "server"
        self.flow.close_code = ws_event.code
        self.flow.close_reason = ws_event.reason

        other.close(ws_event.code, ws_event.reason)
        yield commands.SendData(send_to, other.bytes_to_send())

        # FIXME: Wait for other end to actually send the closing frame
        # FIXME: https://github.com/python-hyper/wsproto/pull/50
        yield commands.SendData(self.context.client if from_client else self.context.server, source.bytes_to_send())

        if ws_event.code != 1000:
            self.flow.error = flow.Error(
                "WebSocket connection closed unexpectedly by {}: {}".format(
                    "client" if from_client else "server",
                    ws_event.reason
                )
            )
            yield commands.Hook("websocket_error", self.flow)
