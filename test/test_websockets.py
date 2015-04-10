from netlib import test
from netlib.websockets import implementations as ws

class TestWebSockets(test.ServerTestBase):
    handler = ws.WebSocketsEchoHandler

    def test_websockets_echo(self):
        msg    = "hello I'm the client"
        client = ws.WebSocketsClient(("127.0.0.1", self.port))
        client.connect()
        client.send_message(msg)
        response = client.read_next_message()
        print "Assert response: " + response + " == msg: " + msg
        assert response == msg

