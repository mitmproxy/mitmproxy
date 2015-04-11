from netlib import test
from netlib.websockets import implementations as impl
from netlib.websockets import websockets as ws
import os

class TestWebSockets(test.ServerTestBase):
    handler = impl.WebSocketsEchoHandler

    def echo(self, msg):
        client = impl.WebSocketsClient(("127.0.0.1", self.port))
        client.connect()
        client.send_message(msg)
        response = client.read_next_message()
        print "Assert response: " + response + " == msg: " + msg
        assert response == msg

    def test_simple_echo(self):
        self.echo("hello I'm the client")

    def test_frame_sizes(self):
        small_string     =  os.urandom(100)   # length can fit in the the 7 bit payload length 
        medium_string    =  os.urandom(50000) # 50kb, sligthly larger than can fit in a 7 bit int
        large_string     =  os.urandom(150000) # 150kb, slightly larger than can fit in a 16 bit int

        self.echo(small_string)
        self.echo(medium_string)
        self.echo(large_string)


