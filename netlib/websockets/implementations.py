from netlib import tcp
from base64 import b64encode
from StringIO import StringIO
from . import websockets as ws
import struct
import SocketServer
import os

# Simple websocket client and servers that are used to exercise the functionality in websockets.py
# These are *not* fully RFC6455 compliant

class WebSocketsEchoHandler(tcp.BaseHandler):
    def __init__(self, connection, address, server):
        super(WebSocketsEchoHandler, self).__init__(connection, address, server)
        self.handshake_done = False

    def handle(self):
       while True:
          if not self.handshake_done:
              self.handshake()
          else:
              self.read_next_message()

    def read_next_message(self):
        decoded = ws.Frame.from_byte_stream(self.rfile.read).decoded_payload
        self.on_message(decoded)

    def send_message(self, message):
        frame = ws.Frame.default(message, from_client = False)
        self.wfile.write(frame.safe_to_bytes())
        self.wfile.flush()

    def handshake(self):
        client_hs = ws.read_handshake(self.rfile.read, 1)
        key       = ws.process_handshake_from_client(client_hs)
        response  = ws.create_server_handshake(key)
        self.wfile.write(response)
        self.wfile.flush()
        self.handshake_done = True

    def on_message(self, message):
        if message is not None:
            self.send_message(message)


class WebSocketsClient(tcp.TCPClient):
    def __init__(self, address, source_address=None):
        super(WebSocketsClient, self).__init__(address, source_address)
        self.version       = "13"
        self.client_nounce = ws.create_client_nounce()
        self.resource      = "/"

    def connect(self):
        super(WebSocketsClient, self).connect()

        handshake = ws.create_client_handshake(
            self.address.host,
            self.address.port,
            self.client_nounce,
            self.version,
            self.resource
        )

        self.wfile.write(handshake)
        self.wfile.flush()

        server_handshake = ws.read_handshake(self.rfile.read, 1)

        server_nounce = ws.process_handshake_from_server(server_handshake, self.client_nounce)

        if not server_nounce == ws.create_server_nounce(self.client_nounce):
            self.close()

    def read_next_message(self):
        return ws.Frame.from_byte_stream(self.rfile.read).payload

    def send_message(self, message):
        frame = ws.Frame.default(message, from_client = True)
        self.wfile.write(frame.safe_to_bytes())
        self.wfile.flush()
