from mitmproxy import websocket, http, flow
from mitmproxy.proxy2 import events, commands
from mitmproxy.proxy2.context import Context
from mitmproxy.proxy2.layer import Layer
from mitmproxy.proxy2.utils import expect
from wsproto import connection as wsconn
from wsproto import events as wsevents


class WebsocketLayer(Layer):
    """
    Simple TCP layer that just relays messages right now.
    """
    context: Context = None
    flow: websocket.WebSocketFlow

    def __init__(self, context: Context, handshake_flow: http.HTTPFlow):
        super().__init__(context)
        self.flow = websocket.WebSocketFlow(context.client, context.server, handshake_flow)
        assert context.server.connected
        self.client_frame_buffer = []
        self.server_frame_buffer = []
        extension = self.flow.server_extensions
        self.client_conn = wsconn.WSConnection(wsconn.SERVER, wsconn.ConnectionState.OPEN,
                                               extensions=[extension] if extension else None)

        self.server_conn = wsconn.WSConnection(wsconn.CLIENT, wsconn.ConnectionState.OPEN,
                                               extensions=[extension] if extension else None)

    @expect(events.Start)
    def start(self, _) -> commands.TCommandGenerator:
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

            for ws_event in source.events():
                if isinstance(ws_event, wsevents.DataReceived):
                    fb.append(ws_event.data)
                    if ws_event.message_finished:
                        if isinstance(ws_event, wsevents.BytesReceived):
                            payload = b"".join(fb)
                        else:
                            payload = "".join(fb)
                        fb.clear()
                        websocket_message = websocket.WebSocketMessage(0x1 if isinstance(ws_event, wsevents.TextReceived) else 0x2,
                                                                       from_client, payload)
                        self.flow.messages.append(websocket_message)
                        yield commands.Hook("websocket_message", self.flow)

                    other.send_data(ws_event.data, ws_event.message_finished)
                    yield commands.SendData(send_to, other.bytes_to_send())
                elif isinstance(ws_event, wsevents.PingReceived):
                    yield commands.Log(
                        "info",
                        "Websocket PING received {}".format(ws_event.payload.decode())
                    )
                    other.ping()
                    yield commands.SendData(send_to, other.bytes_to_send())
                    yield commands.SendData(self.context.client if from_client else self.context.server, source.bytes_to_send())
                elif isinstance(ws_event, wsevents.PongReceived):
                    yield commands.Log(
                        "info",
                        "Websocket PONG received {}".format(ws_event.payload.decode())
                    )

                elif isinstance(ws_event, wsevents.ConnectionClosed):
                    other.close(ws_event.code, ws_event.reason)
                    yield commands.SendData(send_to, other.bytes_to_send())
                    # FIXME: Wait for other end to actually send the closing frame
                    yield commands.SendData(self.context.client if from_client else self.context.server, source.bytes_to_send())

                    if ws_event.code != 1000:
                        self.flow.error = flow.Error(
                            "WebSocket connection closed unexpectedly by {}: {}".format(
                                "client" if from_client else "server",
                                ws_event.reason
                            )
                        )
                        yield commands.Hook("websocket_error", self.flow)

                    yield commands.Hook("websocket_end", self.flow)
                    if not from_client:
                        yield commands.CloseConnection(self.context.client)
                    self._handle_event = self.done
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
