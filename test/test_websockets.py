from netlib import tcp
from netlib import test
from netlib import websockets
import os
from nose.tools import raises


class WebSocketsEchoHandler(tcp.BaseHandler):
    def __init__(self, connection, address, server):
        super(WebSocketsEchoHandler, self).__init__(
            connection, address, server
        )
        self.handshake_done = False

    def handle(self):
        while True:
            if not self.handshake_done:
                self.handshake()
            else:
                self.read_next_message()

    def read_next_message(self):
        decoded = websockets.Frame.from_byte_stream(self.rfile.read).decoded_payload
        self.on_message(decoded)

    def send_message(self, message):
        frame = websockets.Frame.default(message, from_client = False)
        self.wfile.write(frame.safe_to_bytes())
        self.wfile.flush()

    def handshake(self):
        client_hs = websockets.read_handshake(self.rfile.read, 1)
        key = websockets.process_handshake_from_client(client_hs)
        response = websockets.create_server_handshake(key)
        self.wfile.write(response)
        self.wfile.flush()
        self.handshake_done = True

    def on_message(self, message):
        if message is not None:
            self.send_message(message)


class WebSocketsClient(tcp.TCPClient):
    def __init__(self, address, source_address=None):
        super(WebSocketsClient, self).__init__(address, source_address)
        self.version = "13"
        self.client_nounce = websockets.create_client_nounce()
        self.resource = "/"

    def connect(self):
        super(WebSocketsClient, self).connect()

        handshake = websockets.create_client_handshake(
            self.address.host,
            self.address.port,
            self.client_nounce,
            self.version,
            self.resource
        )

        self.wfile.write(handshake)
        self.wfile.flush()

        server_handshake = websockets.read_handshake(self.rfile.read, 1)
        server_nounce = websockets.process_handshake_from_server(
            server_handshake, self.client_nounce
        )

        if not server_nounce == websockets.create_server_nounce(self.client_nounce):
            self.close()

    def read_next_message(self):
        return websockets.Frame.from_byte_stream(self.rfile.read).payload

    def send_message(self, message):
        frame = websockets.Frame.default(message, from_client = True)
        self.wfile.write(frame.safe_to_bytes())
        self.wfile.flush()


class TestWebSockets(test.ServerTestBase):
    handler = WebSocketsEchoHandler

    def random_bytes(self, n = 100):
        return os.urandom(n)

    def echo(self, msg):
        client = WebSocketsClient(("127.0.0.1", self.port))
        client.connect()
        client.send_message(msg)
        response = client.read_next_message()
        assert response == msg

    def test_simple_echo(self):
        self.echo("hello I'm the client")

    def test_frame_sizes(self):
        # length can fit in the the 7 bit payload length
        small_msg = self.random_bytes(100)
        # 50kb, sligthly larger than can fit in a 7 bit int
        medium_msg = self.random_bytes(50000)
        # 150kb, slightly larger than can fit in a 16 bit int
        large_msg = self.random_bytes(150000)

        self.echo(small_msg)
        self.echo(medium_msg)
        self.echo(large_msg)

    def test_default_builder(self):
        """
          default builder should always generate valid frames
        """
        msg = self.random_bytes()
        client_frame = websockets.Frame.default(msg, from_client = True)
        assert client_frame.is_valid()

        server_frame = websockets.Frame.default(msg, from_client = False)
        assert server_frame.is_valid()

    def test_serialization_bijection(self):
        """
          Ensure that various frame types can be serialized/deserialized back
          and forth between to_bytes() and from_bytes()
        """
        for is_client in [True, False]:
            for num_bytes in [100, 50000, 150000]:
                frame = websockets.Frame.default(
                    self.random_bytes(num_bytes), is_client
                )
                assert frame == websockets.Frame.from_bytes(frame.to_bytes())

        bytes = b'\x81\x11cba'
        assert websockets.Frame.from_bytes(bytes).to_bytes() == bytes

    @raises(websockets.WebSocketFrameValidationException)
    def test_safe_to_bytes(self):
        frame = websockets.Frame.default(self.random_bytes(8))
        frame.actual_payload_length = 1 # corrupt the frame
        frame.safe_to_bytes()


class BadHandshakeHandler(WebSocketsEchoHandler):
    def handshake(self):
        client_hs = websockets.read_handshake(self.rfile.read, 1)
        websockets.process_handshake_from_client(client_hs)
        response = websockets.create_server_handshake("malformed_key")
        self.wfile.write(response)
        self.wfile.flush()
        self.handshake_done = True


class TestBadHandshake(test.ServerTestBase):
    """
      Ensure that the client disconnects if the server handshake is malformed
    """
    handler = BadHandshakeHandler

    @raises(tcp.NetLibDisconnect)
    def test(self):
        client = WebSocketsClient(("127.0.0.1", self.port))
        client.connect()
        client.send_message("hello")
