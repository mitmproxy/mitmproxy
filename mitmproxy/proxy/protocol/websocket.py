import os
import socket
import struct
from OpenSSL import SSL

from wsproto import events
from wsproto.connection import ConnectionType, WSConnection
from wsproto.extensions import PerMessageDeflate

from mitmproxy import exceptions
from mitmproxy import flow
from mitmproxy.proxy.protocol import base
from mitmproxy.net import http
from mitmproxy.net import tcp
from mitmproxy.net import websockets
from mitmproxy.websocket import WebSocketFlow, WebSocketMessage


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
        self.flow = None  # type: WebSocketFlow

        self.client_frame_buffer = []
        self.server_frame_buffer = []

        self.connections = {}  # type: Dict[object, WSConnection]

        extensions = []
        if 'Sec-WebSocket-Extensions' in handshake_flow.response.headers:
            if PerMessageDeflate.name in handshake_flow.response.headers['Sec-WebSocket-Extensions']:
                extensions = [PerMessageDeflate.name]

        self.connections[self.client_conn] = WSConnection(ConnectionType.SERVER,
                                                          extensions=extensions)
        self.connections[self.server_conn] = WSConnection(ConnectionType.CLIENT,
                                                          host=handshake_flow.request.host,
                                                          resource=handshake_flow.request.path,
                                                          extensions=extensions)

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
        elif isinstance(event, events.ConnectionFailed):
            return self._handle_connection_closed(event, source_conn, other_conn, is_server)
        elif isinstance(event, events.ConnectionFailed):
            return self._handle_connection_failed(event)

        # fail-safe for unhandled events
        return True

    def _handle_data_received(self, event, source_conn, other_conn, is_server):
        return True

    def _handle_ping_received(self, event, source_conn, other_conn, is_server):
        # PING is automatically answered with a PONG by wsproto
        # TODO: log this PING and its payload
        self.connections[other_conn].ping(event.payload)
        other_conn.send(self.connections[other_conn].bytes_to_send())
        return True

    def _handle_pong_received(self, event, source_conn, other_conn, is_server):
        # TODO: log this PONG and its payload
        self.connections[other_conn].pong(event.payload)
        other_conn.send(self.connections[other_conn].bytes_to_send())
        return True

    def _handle_connection_closed(self, event, source_conn, other_conn, is_server):
        self.flow.close_sender = "server" if is_server else "client"
        self.flow.close_code = event.code
        self.flow.close_reason = event.reason

        print(self.connections[other_conn])
        self.connections[other_conn].close(event.code, event.reason)

        # initiate close handshake
        return False

    def _handle_connection_failed(self, event):
        raise exceptions.TcpException(repr(event))

    # def _handle_data_frame(self, frame, source_conn, other_conn, is_server):
    #
    #     fb = self.server_frame_buffer if is_server else self.client_frame_buffer
    #     fb.append(frame)
    #
    #     if frame.header.fin:
    #         payload = b''.join(f.payload for f in fb)
    #         original_chunk_sizes = [len(f.payload) for f in fb]
    #         message_type = fb[0].header.opcode
    #         compressed_message = fb[0].header.rsv1
    #         fb.clear()
    #
    #         websocket_message = WebSocketMessage(message_type, not is_server, payload)
    #         length = len(websocket_message.content)
    #         self.flow.messages.append(websocket_message)
    #         self.channel.ask("websocket_message", self.flow)
    #
    #         if not self.flow.stream:
    #             def get_chunk(payload):
    #                 if len(payload) == length:
    #                     # message has the same length, we can reuse the same sizes
    #                     pos = 0
    #                     for s in original_chunk_sizes:
    #                         yield payload[pos:pos + s]
    #                         pos += s
    #                 else:
    #                     # just re-chunk everything into 4kB frames
    #                     # header len = 4 bytes without masking key and 8 bytes with masking key
    #                     chunk_size = 4092 if is_server else 4088
    #                     chunks = range(0, len(payload), chunk_size)
    #                     for i in chunks:
    #                         yield payload[i:i + chunk_size]
    #
    #             frms = [
    #                 websockets.Frame(
    #                     payload=chunk,
    #                     opcode=frame.header.opcode,
    #                     mask=(False if is_server else 1),
    #                     masking_key=(b'' if is_server else os.urandom(4)))
    #                 for chunk in get_chunk(websocket_message.content)
    #             ]
    #
    #             if len(frms) > 0:
    #                 frms[-1].header.fin = True
    #             else:
    #                 frms.append(websockets.Frame(
    #                     fin=True,
    #                     opcode=websockets.OPCODE.CONTINUE,
    #                     mask=(False if is_server else 1),
    #                     masking_key=(b'' if is_server else os.urandom(4))))
    #
    #             frms[0].header.opcode = message_type
    #             frms[0].header.rsv1 = compressed_message
    #
    #             for frm in frms:
    #                 other_conn.send(bytes(frm))
    #
    #         else:
    #             other_conn.send(bytes(frame))
    #
    #     elif self.flow.stream:
    #         other_conn.send(bytes(frame))
    #
    #     return True

    def __call__(self):
        self.flow = WebSocketFlow(self.client_conn, self.server_conn, self.handshake_flow, self)
        self.flow.metadata['websocket_handshake'] = self.handshake_flow.id
        self.handshake_flow.metadata['websocket_flow'] = self.flow.id
        self.channel.ask("websocket_start", self.flow)

        conns = [c.connection for c in self.connections.keys()]
        close_received = False

        try:
            while not self.channel.should_exit.is_set():
                r = tcp.ssl_read_select(conns, 0.1)
                for conn in r:
                    source_conn = self.client_conn if conn == self.client_conn.connection else self.server_conn
                    other_conn = self.server_conn if conn == self.client_conn.connection else self.client_conn
                    is_server = (source_conn == self.server_conn)

                    frame = websockets.Frame.from_file(source_conn.rfile)
                    self.connections[source_conn].receive_bytes(bytes(frame))
                    source_conn.send(self.connections[source_conn].bytes_to_send())

                    for event in self.connections[source_conn].events():
                        print('is_server:', is_server, 'event:', event)
                        if not self._handle_event(event, source_conn, other_conn, is_server):
                            if close_received:
                                break
                            else:
                                close_received = True
        except (socket.error, exceptions.TcpException, SSL.Error) as e:
            s = 'server' if is_server else 'client'
            self.flow.error = flow.Error("WebSocket connection closed unexpectedly by {}: {}".format(s, repr(e)))
            self.channel.tell("websocket_error", self.flow)
        finally:
            self.channel.tell("websocket_end", self.flow)
