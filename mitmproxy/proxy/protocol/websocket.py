import queue
import socket
from OpenSSL import SSL


import wsproto
from wsproto import events, WSConnection
from wsproto.connection import ConnectionType
from wsproto.events import AcceptConnection, CloseConnection, Message, Ping, Request
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

        client_extensions = []
        server_extensions = []
        if 'Sec-WebSocket-Extensions' in handshake_flow.response.headers:
            if PerMessageDeflate.name in handshake_flow.response.headers['Sec-WebSocket-Extensions']:
                client_extensions = [PerMessageDeflate()]
                server_extensions = [PerMessageDeflate()]
        self.connections[self.client_conn] = WSConnection(ConnectionType.SERVER)
        self.connections[self.server_conn] = WSConnection(ConnectionType.CLIENT)

        if client_extensions:
            client_extensions[0].finalize(handshake_flow.response.headers['Sec-WebSocket-Extensions'])
        if server_extensions:
            server_extensions[0].finalize(handshake_flow.response.headers['Sec-WebSocket-Extensions'])

        request = Request(extensions=client_extensions, host=handshake_flow.request.host, target=handshake_flow.request.path)
        data = self.connections[self.server_conn].send(request)
        self.connections[self.client_conn].receive_data(data)

        event = next(self.connections[self.client_conn].events())
        assert isinstance(event, events.Request)

        data = self.connections[self.client_conn].send(AcceptConnection(extensions=server_extensions))
        self.connections[self.server_conn].receive_data(data)
        assert isinstance(next(self.connections[self.server_conn].events()), events.AcceptConnection)

    def _handle_event(self, event, source_conn, other_conn, is_server):
        if isinstance(event, events.Message):
            return self._handle_message(event, source_conn, other_conn, is_server)
        elif isinstance(event, events.Ping):
            return self._handle_ping(event, source_conn, other_conn, is_server)
        elif isinstance(event, events.Pong):
            return self._handle_pong(event, source_conn, other_conn, is_server)
        elif isinstance(event, events.CloseConnection):
            return self._handle_close_connection(event, source_conn, other_conn, is_server)

        # fail-safe for unhandled events
        return True  # pragma: no cover

    def _handle_message(self, event, source_conn, other_conn, is_server):
        fb = self.server_frame_buffer if is_server else self.client_frame_buffer
        fb.append(event.data)

        if event.message_finished:
            original_chunk_sizes = [len(f) for f in fb]

            if isinstance(event, events.TextMessage):
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
                    data = self.connections[other_conn].send(Message(data=chunk, message_finished=final))
                    other_conn.send(data)

        if self.flow.stream:
            data = self.connections[other_conn].send(Message(data=event.data, message_finished=event.message_finished))
            other_conn.send(data)
        return True

    def _handle_ping(self, event, source_conn, other_conn, is_server):
        # Use event.response to create the approprate Pong response
        data = self.connections[other_conn].send(Ping())
        other_conn.send(data)
        data = self.connections[source_conn].send(event.response())
        source_conn.send(data)
        self.log(
            "Ping Received from {}".format("server" if is_server else "client"),
            "info",
            [strutils.bytes_to_escaped_str(bytes(event.payload))]
        )
        return True

    def _handle_pong(self, event, source_conn, other_conn, is_server):
        self.log(
            "Pong Received from {}".format("server" if is_server else "client"),
            "info",
            [strutils.bytes_to_escaped_str(bytes(event.payload))]
        )
        return True

    def _handle_close_connection(self, event, source_conn, other_conn, is_server):
        self.flow.close_sender = "server" if is_server else "client"
        self.flow.close_code = event.code
        self.flow.close_reason = event.reason

        data = self.connections[other_conn].send(CloseConnection(code=event.code, reason=event.reason))
        other_conn.send(data)
        data = self.connections[source_conn].send(event.response())
        source_conn.send(data)

        return False

    def _inject_messages(self, endpoint, message_queue):
        while True:
            try:
                payload = message_queue.get_nowait()
                data = self.connections[endpoint].send(Message(data=payload, message_finished=True))
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
                    data = self.connections[source_conn].receive_data(bytes(frame))
                    source_conn.send(data)

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
