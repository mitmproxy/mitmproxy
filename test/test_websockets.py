from netlib import tcp, test, websockets, http
import os
from nose.tools import raises


def test_frame_header_bytes():
    assert websockets.frame_header_bytes()


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
        frame = websockets.Frame.from_file(self.rfile)
        self.on_message(frame.payload)

    def send_message(self, message):
        frame = websockets.Frame.default(message, from_client = False)
        frame.to_file(self.wfile)

    def handshake(self):
        req = http.read_request(self.rfile)
        key = websockets.check_client_handshake(req.headers)

        self.wfile.write(http.response_preamble(101) + "\r\n")
        headers = websockets.server_handshake_headers(key)
        self.wfile.write(headers.format() + "\r\n")
        self.wfile.flush()
        self.handshake_done = True

    def on_message(self, message):
        if message is not None:
            self.send_message(message)


class WebSocketsClient(tcp.TCPClient):
    def __init__(self, address, source_address=None):
        super(WebSocketsClient, self).__init__(address, source_address)
        self.client_nonce = None

    def connect(self):
        super(WebSocketsClient, self).connect()

        preamble = http.request_preamble("GET", "/")
        self.wfile.write(preamble + "\r\n")
        headers = websockets.client_handshake_headers()
        self.client_nonce = headers.get_first("sec-websocket-key")
        self.wfile.write(headers.format() + "\r\n")
        self.wfile.flush()

        resp = http.read_response(self.rfile, "get", None)
        server_nonce = websockets.check_server_handshake(resp.headers)

        if not server_nonce == websockets.create_server_nonce(self.client_nonce):
            self.close()

    def read_next_message(self):
        return websockets.Frame.from_file(self.rfile).payload

    def send_message(self, message):
        frame = websockets.Frame.default(message, from_client = True)
        frame.to_file(self.wfile)


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

        server_frame = websockets.Frame.default(msg, from_client = False)
        assert server_frame.is_valid()

    def test_is_valid(self):
        def f():
            return websockets.Frame.default(self.random_bytes(10), True)

        frame = f()
        assert frame.is_valid()

        frame = f()
        frame.fin = 2
        assert not frame.is_valid()

        frame = f()
        frame.mask_bit = 1
        frame.masking_key = "foobbarboo"
        assert not frame.is_valid()

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
                frame2 = websockets.Frame.from_bytes(
                    frame.to_bytes()
                )
                assert frame == frame2

        bytes = b'\x81\x03cba'
        assert websockets.Frame.from_bytes(bytes).to_bytes() == bytes

    def test_check_server_handshake(self):
        headers = websockets.server_handshake_headers("key")
        assert websockets.check_server_handshake(headers)
        headers["Upgrade"] = ["not_websocket"]
        assert not websockets.check_server_handshake(headers)

    def test_check_client_handshake(self):
        headers = websockets.client_handshake_headers("key")
        assert websockets.check_client_handshake(headers) == "key"
        headers["Upgrade"] = ["not_websocket"]
        assert not websockets.check_client_handshake(headers)


class BadHandshakeHandler(WebSocketsEchoHandler):
    def handshake(self):
        client_hs = http.read_request(self.rfile)
        websockets.check_client_handshake(client_hs.headers)

        self.wfile.write(http.response_preamble(101) + "\r\n")
        headers = websockets.server_handshake_headers("malformed key")
        self.wfile.write(headers.format() + "\r\n")
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
