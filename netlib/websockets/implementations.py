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
        decoded = ws.WebSocketsFrame.from_byte_stream(self.rfile.read).decoded_payload
        self.on_message(decoded)

    def send_message(self, message):
        frame = ws.WebSocketsFrame.default(message, from_client = False)
        self.wfile.write(frame.safe_to_bytes())
        self.wfile.flush()
 
    def handshake(self):
        client_hs = ws.read_handshake(self.rfile.read, 1)
        key       = ws.server_process_handshake(client_hs)
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
        self.version    = "13"
        self.key        = ws.generate_client_nounce()
        self.resource   = "/"

    def connect(self):
        super(WebSocketsClient, self).connect()

        handshake = ws.create_client_handshake(
            self.address.host,
            self.address.port,
            self.key,
            self.version,
            self.resource
        )

        self.wfile.write(handshake)
        self.wfile.flush()

        response = ws.read_handshake(self.rfile.read, 1)
        
        if not response:
            self.close()

    def read_next_message(self):
        try:
            return ws.WebSocketsFrame.from_byte_stream(self.rfile.read).payload
        except IndexError:
            self.close()
 
    def send_message(self, message):
        frame = ws.WebSocketsFrame.default(message, from_client = True)
        self.wfile.write(frame.safe_to_bytes())
        self.wfile.flush()
