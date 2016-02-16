import os

from netlib.http.http1 import read_response, read_request

from netlib import tcp, websockets, http, tutils
from netlib.http import status_codes
from netlib.tutils import treq
from netlib.exceptions import *

from .. import tservers

class WebSocketsEchoHandler(tcp.BaseHandler):

    def __init__(self, connection, address, server):
        super(WebSocketsEchoHandler, self).__init__(
            connection, address, server
        )
        self.protocol = websockets.WebsocketsProtocol()
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
        frame = websockets.Frame.default(message, from_client=False)
        frame.to_file(self.wfile)

    def handshake(self):

        req = read_request(self.rfile)
        key = self.protocol.check_client_handshake(req.headers)

        preamble = 'HTTP/1.1 101 %s' % status_codes.RESPONSES.get(101)
        self.wfile.write(preamble.encode() + b"\r\n")
        headers = self.protocol.server_handshake_headers(key)
        self.wfile.write(str(headers) + "\r\n")
        self.wfile.flush()
        self.handshake_done = True

    def on_message(self, message):
        if message is not None:
            self.send_message(message)


class WebSocketsClient(tcp.TCPClient):

    def __init__(self, address, source_address=None):
        super(WebSocketsClient, self).__init__(address, source_address)
        self.protocol = websockets.WebsocketsProtocol()
        self.client_nonce = None

    def connect(self):
        super(WebSocketsClient, self).connect()

        preamble = b'GET / HTTP/1.1'
        self.wfile.write(preamble + b"\r\n")
        headers = self.protocol.client_handshake_headers()
        self.client_nonce = headers["sec-websocket-key"].encode("ascii")
        self.wfile.write(bytes(headers) + b"\r\n")
        self.wfile.flush()

        resp = read_response(self.rfile, treq(method=b"GET"))
        server_nonce = self.protocol.check_server_handshake(resp.headers)

        if not server_nonce == self.protocol.create_server_nonce(self.client_nonce):
            self.close()

    def read_next_message(self):
        return websockets.Frame.from_file(self.rfile).payload

    def send_message(self, message):
        frame = websockets.Frame.default(message, from_client=True)
        frame.to_file(self.wfile)


class TestWebSockets(tservers.ServerTestBase):
    handler = WebSocketsEchoHandler

    def __init__(self):
        self.protocol = websockets.WebsocketsProtocol()

    def random_bytes(self, n=100):
        return os.urandom(n)

    def echo(self, msg):
        client = WebSocketsClient(("127.0.0.1", self.port))
        client.connect()
        client.send_message(msg)
        response = client.read_next_message()
        assert response == msg

    def test_simple_echo(self):
        self.echo(b"hello I'm the client")

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
        client_frame = websockets.Frame.default(msg, from_client=True)
        server_frame = websockets.Frame.default(msg, from_client=False)

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
        headers = self.protocol.server_handshake_headers("key")
        assert self.protocol.check_server_handshake(headers)
        headers["Upgrade"] = "not_websocket"
        assert not self.protocol.check_server_handshake(headers)

    def test_check_client_handshake(self):
        headers = self.protocol.client_handshake_headers("key")
        assert self.protocol.check_client_handshake(headers) == "key"
        headers["Upgrade"] = "not_websocket"
        assert not self.protocol.check_client_handshake(headers)


class BadHandshakeHandler(WebSocketsEchoHandler):

    def handshake(self):

        client_hs = read_request(self.rfile)
        self.protocol.check_client_handshake(client_hs.headers)

        preamble = 'HTTP/1.1 101 %s\r\n' % status_codes.RESPONSES.get(101)
        self.wfile.write(preamble.encode())
        headers = self.protocol.server_handshake_headers(b"malformed key")
        self.wfile.write(bytes(headers) + b"\r\n")
        self.wfile.flush()
        self.handshake_done = True


class TestBadHandshake(tservers.ServerTestBase):

    """
      Ensure that the client disconnects if the server handshake is malformed
    """
    handler = BadHandshakeHandler

    def test(self):
        with tutils.raises(TcpDisconnect):
            client = WebSocketsClient(("127.0.0.1", self.port))
            client.connect()
            client.send_message(b"hello")


class TestFrameHeader:

    def test_roundtrip(self):
        def round(*args, **kwargs):
            f = websockets.FrameHeader(*args, **kwargs)
            f2 = websockets.FrameHeader.from_file(tutils.treader(bytes(f)))
            assert f == f2
        round()
        round(fin=1)
        round(rsv1=1)
        round(rsv2=1)
        round(rsv3=1)
        round(payload_length=1)
        round(payload_length=100)
        round(payload_length=1000)
        round(payload_length=10000)
        round(opcode=websockets.OPCODE.PING)
        round(masking_key=b"test")

    def test_human_readable(self):
        f = websockets.FrameHeader(
            masking_key=b"test",
            fin=True,
            payload_length=10
        )
        assert repr(f)
        f = websockets.FrameHeader()
        assert repr(f)

    def test_funky(self):
        f = websockets.FrameHeader(masking_key=b"test", mask=False)
        raw = bytes(f)
        f2 = websockets.FrameHeader.from_file(tutils.treader(raw))
        assert not f2.mask

    def test_violations(self):
        tutils.raises("opcode", websockets.FrameHeader, opcode=17)
        tutils.raises("masking key", websockets.FrameHeader, masking_key=b"x")

    def test_automask(self):
        f = websockets.FrameHeader(mask=True)
        assert f.masking_key

        f = websockets.FrameHeader(masking_key=b"foob")
        assert f.mask

        f = websockets.FrameHeader(masking_key=b"foob", mask=0)
        assert not f.mask
        assert f.masking_key


class TestFrame:

    def test_roundtrip(self):
        def round(*args, **kwargs):
            f = websockets.Frame(*args, **kwargs)
            raw = bytes(f)
            f2 = websockets.Frame.from_file(tutils.treader(raw))
            assert f == f2
        round(b"test")
        round(b"test", fin=1)
        round(b"test", rsv1=1)
        round(b"test", opcode=websockets.OPCODE.PING)
        round(b"test", masking_key=b"test")

    def test_human_readable(self):
        f = websockets.Frame()
        assert repr(f)


def test_masker():
    tests = [
        [b"a"],
        [b"four"],
        [b"fourf"],
        [b"fourfive"],
        [b"a", b"aasdfasdfa", b"asdf"],
        [b"a" * 50, b"aasdfasdfa", b"asdf"],
    ]
    for i in tests:
        m = websockets.Masker(b"abcd")
        data = b"".join([m(t) for t in i])
        data2 = websockets.Masker(b"abcd")(data)
        assert data2 == b"".join(i)
