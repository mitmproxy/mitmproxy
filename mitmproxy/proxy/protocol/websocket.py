import queue
import socket
from OpenSSL import SSL


import wsproto
from wsproto import events
from wsproto.connection import ConnectionType, WSConnection
from wsproto.extensions import PerMessageDeflate

from mitmproxy import exceptions
from mitmproxy import flow
from mitmproxy.proxy.protocol import base
from mitmproxy.net import tcp
from mitmproxy.net import websockets
from mitmproxy.websocket import WebSocketFlow, WebSocketMessage
from mitmproxy.utils import strutils


class WebSocketLayer(base.Layer):
    """
        WebSocket layer to intercept, modify, and forward WebSocket messages.

        Only version 13 is supported (as specified in RFC6455).
        Only HTTP/1.1-initiated connections are supported.

        The client starts by sending an Upgrade-request.
        In order to determine the handshake and negotiate the correct protocol
        and extensions, the Upgrade-request is forwarded to the server.
        The response from the server is then parsed and negotiated settings are extracted.
        Finally the handshake is completed by forwarding the server-response to the client.
        After that, only WebSocket frames are exchanged.

        PING/PONG frames pass through and must be answered by the other endpoint.

        CLOSE frames are forwarded before this WebSocketLayer terminates.

        This layer is transparent to any negotiated extensions.
        This layer is transparent to any negotiated subprotocols.
        Only raw frames are forwarded to the other endpoint.

        WebSocket messages are stored in a WebSocketFlow.
    """

    def __init__(self, ctx, handshake_flow):
        super().__init__(ctx)
        self.handshake_flow = handshake_flow
        self.flow: WebSocketFlow = None

        self.client_frame_buffer = []
        self.server_frame_buffer = []

        self.connections: dict[object, WSConnection] = {}

        extensions = []
        if 'Sec-WebSocket-Extensions' in handshake_flow.response.headers:
            if PerMessageDeflate.name in handshake_flow.response.headers['Sec-WebSocket-Extensions']:
                extensions = [PerMessageDeflate()]
        self.connections[self.client_conn] = WSConnection(ConnectionType.SERVER,
                                                          extensions=extensions)
        self.connections[self.server_conn] = WSConnection(ConnectionType.CLIENT,
                                                          host=handshake_flow.request.host,
                                                          resource=handshake_flow.request.path,
                                                          extensions=extensions)
        if extensions:
            for conn in self.connections.values():
                conn.extensions[0].finalize(conn, handshake_flow.response.headers['Sec-WebSocket-Extensions'])

        data = self.connections[self.server_conn].bytes_to_send()
        self.connections[self.client_conn].receive_bytes(data)

        event = next(self.connections[self.client_conn].events())
        assert isinstance(event, events.ConnectionRequested)

        self.connections[self.client_conn].accept(event)
        self.connections[self.server_conn].receive_bytes(self.connections[self.client_conn].bytes_to_send())
        assert isinstance(next(self.connections[self.server_conn].events()), events.ConnectionEstablished)

    def _handle_event(self, event, source_conn, other_conn, is_server):
        if isinstance(event, events.DataReceived):
            return self._handle_data_received(event, source_conn, other_conn, is_server)
        elif isinstance(event, events.PingReceived):
            return self._handle_ping_received(event, source_conn, other_conn, is_server)
        elif isinstance(event, events.PongReceived):
            return self._handle_pong_received(event, source_conn, other_conn, is_server)
        elif isinstance(event, events.ConnectionClosed):
            return self._handle_connection_closed(event, source_conn, other_conn, is_server)

        # fail-safe for unhandled events
        return True  # pragma: no cover

    def _handle_data_received(self, event, source_conn, other_conn, is_server):
        fb = self.server_frame_buffer if is_server else self.client_frame_buffer
        fb.append(event.data)

        if event.message_finished:
            original_chunk_sizes = [len(f) for f in fb]

            if isinstance(event, events.TextReceived):
                message_type = wsproto.frame_protocol.Opcode.TEXT
                payload = ''.join(fb)
            else:
                message_type = wsproto.frame_protocol.Opcode.BINARY
                payload = b''.join(fb)

            fb.clear()

            websocket_message = WebSocketMessage(message_type, not is_server, payload)
            length = len(websocket_message.content)
            self.flow.messages.append(websocket_message)
            self.channel.ask("websocket_message", self.flow)

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
                        chunk_size = 4092 if is_server else 4088
                        chunks = range(0, len(payload), chunk_size)
                        for i in chunks:
                            yield (payload[i:i + chunk_size], True if i + chunk_size >= len(payload) else False)

                for chunk, final in get_chunk(websocket_message.content):
                    self.connections[other_conn].send_data(chunk, final)
                    other_conn.send(self.connections[other_conn].bytes_to_send())

        if self.flow.stream:
            self.connections[other_conn].send_data(event.data, event.message_finished)
            other_conn.send(self.connections[other_conn].bytes_to_send())
        return True

    def _handle_ping_received(self, event, source_conn, other_conn, is_server):
        # PING is automatically answered with a PONG by wsproto
        self.connections[other_conn].ping()
        other_conn.send(self.connections[other_conn].bytes_to_send())
        source_conn.send(self.connections[source_conn].bytes_to_send())
        self.log(
            "Ping Received from {}".format("server" if is_server else "client"),
            "info",
            [strutils.bytes_to_escaped_str(bytes(event.payload))]
        )
        return True

    def _handle_pong_received(self, event, source_conn, other_conn, is_server):
        self.log(
            "Pong Received from {}".format("server" if is_server else "client"),
            "info",
            [strutils.bytes_to_escaped_str(bytes(event.payload))]
        )
        return True

    def _handle_connection_closed(self, event, source_conn, other_conn, is_server):
        self.flow.close_sender = "server" if is_server else "client"
        self.flow.close_code = event.code
        self.flow.close_reason = event.reason

        self.connections[other_conn].close(event.code, event.reason)
        other_conn.send(self.connections[other_conn].bytes_to_send())
        source_conn.send(self.connections[source_conn].bytes_to_send())

        return False

    def _inject_messages(self, endpoint, message_queue):
        while True:
            try:
                payload = message_queue.get_nowait()
                self.connections[endpoint].send_data(payload, final=True)
                data = self.connections[endpoint].bytes_to_send()
                endpoint.send(data)
            except queue.Empty:
                break

    def __call__(self):
        self.flow = WebSocketFlow(self.client_conn, self.server_conn, self.handshake_flow)
        self.flow.metadata['websocket_handshake'] = self.handshake_flow.id
        self.handshake_flow.metadata['websocket_flow'] = self.flow.id
        self.channel.ask("websocket_start", self.flow)

        conns = [c.connection for c in self.connections.keys()]
        close_received = False

        try:
            while not self.channel.should_exit.is_set():
                self._inject_messages(self.client_conn, self.flow._inject_messages_client)
                self._inject_messages(self.server_conn, self.flow._inject_messages_server)

                r = tcp.ssl_read_select(conns, 0.1)
                for conn in r:
                    source_conn = self.client_conn if conn == self.client_conn.connection else self.server_conn
                    other_conn = self.server_conn if conn == self.client_conn.connection else self.client_conn
                    is_server = (source_conn == self.server_conn)

                    frame = websockets.Frame.from_file(source_conn.rfile)
                    self.connections[source_conn].receive_bytes(bytes(frame))
                    source_conn.send(self.connections[source_conn].bytes_to_send())

                    if close_received:
                        return

                    for event in self.connections[source_conn].events():
                        if not self._handle_event(event, source_conn, other_conn, is_server):
                            if not close_received:
                                close_received = True
        except (socket.error, exceptions.TcpException, SSL.Error) as e:
            s = 'server' if is_server else 'client'
            self.flow.error = flow.Error("WebSocket connection closed unexpectedly by {}: {}".format(s, repr(e)))
            self.channel.tell("websocket_error", self.flow)
        finally:
            self.flow.ended = True
            self.channel.tell("websocket_end", self.flow)
