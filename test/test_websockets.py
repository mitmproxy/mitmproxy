from netlib import tcp
from netlib import test
from netlib.websockets import implementations as impl
from netlib.websockets import websockets as ws
import os
from nose.tools import raises

class TestWebSockets(test.ServerTestBase):
    handler = impl.WebSocketsEchoHandler

    def random_bytes(self, n = 100):
        return os.urandom(n)

    def echo(self, msg):
        client = impl.WebSocketsClient(("127.0.0.1", self.port))
        client.connect()
        client.send_message(msg)
        response = client.read_next_message()
        assert response == msg

    def test_simple_echo(self):
        self.echo("hello I'm the client")

    def test_frame_sizes(self):
        small_msg  = self.random_bytes(100)   # length can fit in the the 7 bit payload length 
        medium_msg = self.random_bytes(50000) # 50kb, sligthly larger than can fit in a 7 bit int
        large_msg  = self.random_bytes(150000) # 150kb, slightly larger than can fit in a 16 bit int

        self.echo(small_msg)
        self.echo(medium_msg)
        self.echo(large_msg)

    def test_default_builder(self):
        """
          default builder should always generate valid frames
        """ 
        msg = self.random_bytes()
        client_frame = ws.WebSocketsFrame.default(msg, from_client = True)
        assert client_frame.is_valid()

        server_frame = ws.WebSocketsFrame.default(msg, from_client = False)
        assert server_frame.is_valid()

    def test_serialization_bijection(self):
        for is_client in [True, False]:
          for num_bytes in [100, 50000, 150000]:
            frame = ws.WebSocketsFrame.default(self.random_bytes(num_bytes), is_client)
            assert frame == ws.WebSocketsFrame.from_bytes(frame.to_bytes())

        bytes = b'\x81\x11cba'
        assert ws.WebSocketsFrame.from_bytes(bytes).to_bytes() == bytes


class BadHandshakeHandler(impl.WebSocketsEchoHandler):
    def handshake(self):
        client_hs = ws.read_handshake(self.rfile.read, 1)
        key       = ws.process_handshake_from_client(client_hs)
        response  = ws.create_server_handshake("malformed_key")
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
        client = impl.WebSocketsClient(("127.0.0.1", self.port))
        client.connect()
        client.send_message("hello")