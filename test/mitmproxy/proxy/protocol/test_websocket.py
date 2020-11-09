import pytest
import os
import struct
import tempfile
import traceback

from wsproto.frame_protocol import Opcode

from mitmproxy import exceptions, options
from mitmproxy.http import HTTPFlow, make_connect_request
from mitmproxy.websocket import WebSocketFlow
from mitmproxy.net import http, tcp, websocket

from pathod.language import websockets_frame

from ...net import tservers as net_tservers
from ... import tservers


class _WebSocketServerBase(net_tservers.ServerTestBase):

    class handler(tcp.BaseHandler):

        def handle(self):
            try:
                request = http.http1.read_request(self.rfile)
                assert websocket.check_handshake(request.headers)

                response = http.Response(
                    http_version=b"HTTP/1.1",
                    status_code=101,
                    reason=http.status_codes.RESPONSES.get(101).encode(),
                    headers=http.Headers(
                        connection='upgrade',
                        upgrade='websocket',
                        sec_websocket_accept=b'',
                        sec_websocket_extensions='permessage-deflate' if "permessage-deflate" in request.headers.values() else ''
                    ),
                    content=b'',
                    trailers=None,
                    timestamp_start=0,
                    timestamp_end=0,
                )
                self.wfile.write(http.http1.assemble_response(response))
                self.wfile.flush()

                self.server.handle_websockets(self.rfile, self.wfile)
            except:
                traceback.print_exc()


class _WebSocketTestBase:
    client = None

    @classmethod
    def setup_class(cls):
        cls.options = cls.get_options()
        cls.proxy = tservers.ProxyThread(tservers.TestMaster, cls.options)
        cls.proxy.start()

    @classmethod
    def teardown_class(cls):
        cls.proxy.shutdown()

    @classmethod
    def get_options(cls):
        opts = options.Options(
            listen_port=0,
            upstream_cert=True,
            ssl_insecure=True,
            websocket=True,
        )
        opts.confdir = os.path.join(tempfile.gettempdir(), "mitmproxy")
        return opts

    @property
    def master(self):
        return self.proxy.tmaster

    def setup(self):
        self.master.reset([])
        self.server.server.handle_websockets = self.handle_websockets

    def teardown(self):
        if self.client:
            self.client.close()

    def setup_connection(self, extension=False):
        self.client = tcp.TCPClient(("127.0.0.1", self.proxy.port))
        self.client.connect()

        request = make_connect_request(("127.0.0.1", self.server.server.address[1]))
        self.client.wfile.write(http.http1.assemble_request(request))
        self.client.wfile.flush()

        response = http.http1.read_response(self.client.rfile, request)

        if self.ssl:
            self.client.convert_to_tls()
            assert self.client.tls_established

        request = http.Request(
            host="127.0.0.1",
            port=self.server.server.address[1],
            method=b"GET",
            scheme=b"http",
            authority=b"",
            path=b"/ws",
            http_version=b"HTTP/1.1",
            headers=http.Headers(
                connection="upgrade",
                upgrade="websocket",
                sec_websocket_version="13",
                sec_websocket_key="1234",
                sec_websocket_extensions="permessage-deflate" if extension else ""
            ),
            content=b'',
            trailers=None,
            timestamp_start=0,
            timestamp_end=0,
        )
        self.client.wfile.write(http.http1.assemble_request(request))
        self.client.wfile.flush()

        response = http.http1.read_response(self.client.rfile, request)
        assert websocket.check_handshake(response.headers)


class _WebSocketTest(_WebSocketTestBase, _WebSocketServerBase):

    @classmethod
    def setup_class(cls):
        _WebSocketTestBase.setup_class()
        _WebSocketServerBase.setup_class(ssl=cls.ssl)

    @classmethod
    def teardown_class(cls):
        _WebSocketTestBase.teardown_class()
        _WebSocketServerBase.teardown_class()


class TestSimple(_WebSocketTest):

    @classmethod
    def handle_websockets(cls, rfile, wfile):
        wfile.write(bytes(websockets_frame.Frame(fin=1, opcode=Opcode.TEXT, payload=b'server-foobar')))
        wfile.flush()

        header, frame, _ = websocket.read_frame(rfile)
        wfile.write(bytes(websockets_frame.Frame(fin=1, opcode=header.opcode, payload=frame.payload)))
        wfile.flush()

        header, frame, _ = websocket.read_frame(rfile)
        wfile.write(bytes(websockets_frame.Frame(fin=1, opcode=header.opcode, payload=frame.payload)))
        wfile.flush()

    @pytest.mark.parametrize('streaming', [True, False])
    def test_simple(self, streaming):
        class Stream:
            def websocket_start(self, f):
                f.stream = streaming

        self.proxy.set_addons(Stream())
        self.setup_connection()

        _, frame, _ = websocket.read_frame(self.client.rfile)
        assert frame.payload == b'server-foobar'

        self.client.wfile.write(bytes(websockets_frame.Frame(fin=1, mask=1, opcode=Opcode.TEXT, payload=b'self.client-foobar')))
        self.client.wfile.flush()

        _, frame, _ = websocket.read_frame(self.client.rfile)
        assert frame.payload == b'self.client-foobar'

        self.client.wfile.write(bytes(websockets_frame.Frame(fin=1, mask=1, opcode=Opcode.BINARY, payload=b'\xde\xad\xbe\xef')))
        self.client.wfile.flush()

        _, frame, _ = websocket.read_frame(self.client.rfile)
        assert frame.payload == b'\xde\xad\xbe\xef'

        self.client.wfile.write(bytes(websockets_frame.Frame(fin=1, mask=1, opcode=Opcode.CLOSE)))
        self.client.wfile.flush()

        assert len(self.master.state.flows) == 2
        assert isinstance(self.master.state.flows[0], HTTPFlow)
        assert isinstance(self.master.state.flows[1], WebSocketFlow)
        assert len(self.master.state.flows[1].messages) == 5
        assert self.master.state.flows[1].messages[0].content == 'server-foobar'
        assert self.master.state.flows[1].messages[0].type == Opcode.TEXT
        assert self.master.state.flows[1].messages[1].content == 'self.client-foobar'
        assert self.master.state.flows[1].messages[1].type == Opcode.TEXT
        assert self.master.state.flows[1].messages[2].content == 'self.client-foobar'
        assert self.master.state.flows[1].messages[2].type == Opcode.TEXT
        assert self.master.state.flows[1].messages[3].content == b'\xde\xad\xbe\xef'
        assert self.master.state.flows[1].messages[3].type == Opcode.BINARY
        assert self.master.state.flows[1].messages[4].content == b'\xde\xad\xbe\xef'
        assert self.master.state.flows[1].messages[4].type == Opcode.BINARY

    def test_change_payload(self):
        class Addon:
            def websocket_message(self, f):
                f.messages[-1].content = "foo"

        self.proxy.set_addons(Addon())
        self.setup_connection()

        _, frame, _ = websocket.read_frame(self.client.rfile)
        assert frame.payload == b'foo'

        self.client.wfile.write(bytes(websockets_frame.Frame(fin=1, mask=1, opcode=Opcode.TEXT, payload=b'self.client-foobar')))
        self.client.wfile.flush()

        _, frame, _ = websocket.read_frame(self.client.rfile)
        assert frame.payload == b'foo'

        self.client.wfile.write(bytes(websockets_frame.Frame(fin=1, mask=1, opcode=Opcode.BINARY, payload=b'\xde\xad\xbe\xef')))
        self.client.wfile.flush()

        _, frame, _ = websocket.read_frame(self.client.rfile)
        assert frame.payload == b'foo'


class TestKillFlow(_WebSocketTest):

    @classmethod
    def handle_websockets(cls, rfile, wfile):
        wfile.write(bytes(websockets_frame.Frame(fin=1, opcode=Opcode.TEXT, payload=b'server-foobar')))
        wfile.flush()

    def test_kill(self):
        class KillFlow:
            def websocket_message(self, f):
                f.kill()

        self.proxy.set_addons(KillFlow())
        self.setup_connection()

        with pytest.raises(exceptions.TcpDisconnect):
            _ = websocket.read_frame(self.client.rfile, False)


class TestSimpleTLS(_WebSocketTest):
    ssl = True

    @classmethod
    def handle_websockets(cls, rfile, wfile):
        wfile.write(bytes(websockets_frame.Frame(fin=1, opcode=Opcode.TEXT, payload=b'server-foobar')))
        wfile.flush()

        header, frame, _ = websocket.read_frame(rfile)
        wfile.write(bytes(websockets_frame.Frame(fin=1, opcode=header.opcode, payload=frame.payload)))
        wfile.flush()

    def test_simple_tls(self):
        self.setup_connection()

        _, frame, _ = websocket.read_frame(self.client.rfile)
        assert frame.payload == b'server-foobar'

        self.client.wfile.write(bytes(websockets_frame.Frame(fin=1, mask=1, opcode=Opcode.TEXT, payload=b'self.client-foobar')))
        self.client.wfile.flush()

        _, frame, _ = websocket.read_frame(self.client.rfile)
        assert frame.payload == b'self.client-foobar'

        self.client.wfile.write(bytes(websockets_frame.Frame(fin=1, mask=1, opcode=Opcode.CLOSE)))
        self.client.wfile.flush()


class TestPing(_WebSocketTest):

    @classmethod
    def handle_websockets(cls, rfile, wfile):
        wfile.write(bytes(websockets_frame.Frame(fin=1, opcode=Opcode.PING, payload=b'foobar')))
        wfile.flush()

        header, frame, _ = websocket.read_frame(rfile)
        assert header.opcode == Opcode.PONG
        assert frame.payload == b'foobar'

        wfile.write(bytes(websockets_frame.Frame(fin=1, opcode=Opcode.PONG, payload=b'done')))
        wfile.flush()

        wfile.write(bytes(websockets_frame.Frame(fin=1, opcode=Opcode.CLOSE)))
        wfile.flush()
        _ = websocket.read_frame(rfile, False)

    @pytest.mark.asyncio
    async def test_ping(self):
        self.setup_connection()

        header, frame, _ = websocket.read_frame(self.client.rfile)
        _ = websocket.read_frame(self.client.rfile, False)
        self.client.wfile.write(bytes(websockets_frame.Frame(fin=1, mask=1, opcode=Opcode.CLOSE)))
        self.client.wfile.flush()
        assert header.opcode == Opcode.PING
        assert frame.payload == b''  # We don't send payload to other end

        assert await self.master.await_log("Pong Received from server", "info")


class TestPong(_WebSocketTest):

    @classmethod
    def handle_websockets(cls, rfile, wfile):
        header, frame, _ = websocket.read_frame(rfile)
        assert header.opcode == Opcode.PING
        assert frame.payload == b''

        wfile.write(bytes(websockets_frame.Frame(fin=1, opcode=Opcode.PONG, payload=frame.payload)))
        wfile.flush()

        wfile.write(bytes(websockets_frame.Frame(fin=1, opcode=Opcode.CLOSE)))
        wfile.flush()
        _ = websocket.read_frame(rfile)

    @pytest.mark.asyncio
    async def test_pong(self):
        self.setup_connection()

        self.client.wfile.write(bytes(websockets_frame.Frame(fin=1, mask=1, opcode=Opcode.PING, payload=b'foobar')))
        self.client.wfile.flush()

        header, frame, _ = websocket.read_frame(self.client.rfile)
        _ = websocket.read_frame(self.client.rfile)
        self.client.wfile.write(bytes(websockets_frame.Frame(fin=1, mask=1, opcode=Opcode.CLOSE)))
        self.client.wfile.flush()

        assert header.opcode == Opcode.PONG
        assert frame.payload == b'foobar'
        assert await self.master.await_log("pong received")


class TestClose(_WebSocketTest):

    @classmethod
    def handle_websockets(cls, rfile, wfile):
        header, frame, _ = websocket.read_frame(rfile)
        wfile.write(bytes(websockets_frame.Frame(fin=1, opcode=header.opcode, payload=frame.payload)))
        wfile.write(bytes(websockets_frame.Frame(fin=1, opcode=Opcode.CLOSE)))
        wfile.flush()

        with pytest.raises(exceptions.TcpDisconnect):
            _ = websocket.read_frame(rfile)

    def test_close(self):
        self.setup_connection()

        self.client.wfile.write(bytes(websockets_frame.Frame(fin=1, mask=1, opcode=Opcode.CLOSE)))
        self.client.wfile.flush()

        _ = websocket.read_frame(self.client.rfile)
        with pytest.raises(exceptions.TcpDisconnect):
            _ = websocket.read_frame(self.client.rfile)

    def test_close_payload_1(self):
        self.setup_connection()

        self.client.wfile.write(bytes(websockets_frame.Frame(fin=1, mask=1, opcode=Opcode.CLOSE, payload=b'\00\42')))
        self.client.wfile.flush()

        _ = websocket.read_frame(self.client.rfile)
        with pytest.raises(exceptions.TcpDisconnect):
            _ = websocket.read_frame(self.client.rfile)

    def test_close_payload_2(self):
        self.setup_connection()

        self.client.wfile.write(bytes(websockets_frame.Frame(fin=1, mask=1, opcode=Opcode.CLOSE, payload=b'\00\42foobar')))
        self.client.wfile.flush()

        _ = websocket.read_frame(self.client.rfile)
        with pytest.raises(exceptions.TcpDisconnect):
            _ = websocket.read_frame(self.client.rfile)


class TestInvalidFrame(_WebSocketTest):

    @classmethod
    def handle_websockets(cls, rfile, wfile):
        wfile.write(bytes(websockets_frame.Frame(fin=1, opcode=15, payload=b'foobar')))
        wfile.flush()

    def test_invalid_frame(self):
        self.setup_connection()

        _, frame, _ = websocket.read_frame(self.client.rfile)
        code, = struct.unpack('!H', frame.payload[:2])
        assert code == 1002
        assert frame.payload[2:].startswith(b'Invalid opcode')


class TestStreaming(_WebSocketTest):

    @classmethod
    def handle_websockets(cls, rfile, wfile):
        wfile.write(bytes(websockets_frame.Frame(opcode=Opcode.TEXT, payload=b'server-foobar')))
        wfile.flush()

    @pytest.mark.parametrize('streaming', [True, False])
    def test_streaming(self, streaming):
        class Stream:
            def websocket_start(self, f):
                f.stream = streaming

        self.proxy.set_addons(Stream())
        self.setup_connection()

        frame = None
        if not streaming:
            with pytest.raises(exceptions.TcpDisconnect):  # Reader.safe_read get nothing as result
                _, frame, _ = websocket.read_frame(self.client.rfile)
            assert frame is None

        else:
            _, frame, _ = websocket.read_frame(self.client.rfile)

            assert frame
            assert self.master.state.flows[1].messages == []  # Message not appended as the final frame isn't received


class TestExtension(_WebSocketTest):

    @classmethod
    def handle_websockets(cls, rfile, wfile):
        wfile.write(b'\xc1\x0f*N-*K-\xd2M\xcb\xcfOJ,\x02\x00')
        wfile.flush()

        header, _, _ = websocket.read_frame(rfile)
        assert header.rsv.rsv1
        wfile.write(b'\xc1\nJ\xce\xc9L\xcd+\x81r\x00\x00')
        wfile.flush()

        header, _, _ = websocket.read_frame(rfile)
        assert header.rsv.rsv1
        wfile.write(b'\xc2\x07\xba\xb7v\xdf{\x00\x00')
        wfile.flush()

    def test_extension(self):
        self.setup_connection(True)

        header, _, _ = websocket.read_frame(self.client.rfile)
        assert header.rsv.rsv1

        self.client.wfile.write(b'\xc1\x8fQ\xb7vX\x1by\xbf\x14\x9c\x9c\xa7\x15\x9ax9\x12}\xb5v')
        self.client.wfile.flush()

        header, _, _ = websocket.read_frame(self.client.rfile)
        assert header.rsv.rsv1

        self.client.wfile.write(b'\xc2\x87\xeb\xbb\x0csQ\x0cz\xac\x90\xbb\x0c')
        self.client.wfile.flush()

        header, _, _ = websocket.read_frame(self.client.rfile)
        assert header.rsv.rsv1

        assert len(self.master.state.flows[1].messages) == 5
        assert self.master.state.flows[1].messages[0].content == 'server-foobar'
        assert self.master.state.flows[1].messages[0].type == Opcode.TEXT
        assert self.master.state.flows[1].messages[1].content == 'client-foobar'
        assert self.master.state.flows[1].messages[1].type == Opcode.TEXT
        assert self.master.state.flows[1].messages[2].content == 'client-foobar'
        assert self.master.state.flows[1].messages[2].type == Opcode.TEXT
        assert self.master.state.flows[1].messages[3].content == b'\xde\xad\xbe\xef'
        assert self.master.state.flows[1].messages[3].type == Opcode.BINARY
        assert self.master.state.flows[1].messages[4].content == b'\xde\xad\xbe\xef'
        assert self.master.state.flows[1].messages[4].type == Opcode.BINARY


class TestInjectMessageClient(_WebSocketTest):

    @classmethod
    def handle_websockets(cls, rfile, wfile):
        pass

    def test_inject_message_client(self):
        class Inject:
            def websocket_start(self, flow):
                flow.inject_message(flow.client_conn, 'This is an injected message!')

        self.proxy.set_addons(Inject())
        self.setup_connection()

        header, frame, _ = websocket.read_frame(self.client.rfile)
        assert header.opcode == Opcode.TEXT
        assert frame.payload == b'This is an injected message!'


class TestInjectMessageServer(_WebSocketTest):

    @classmethod
    def handle_websockets(cls, rfile, wfile):
        header, frame, _ = websocket.read_frame(rfile)
        assert header.opcode == Opcode.TEXT
        success = frame.payload == b'This is an injected message!'

        wfile.write(bytes(websockets_frame.Frame(fin=1, opcode=Opcode.TEXT, payload=str(success).encode())))
        wfile.flush()

    def test_inject_message_server(self):
        class Inject:
            def websocket_start(self, flow):
                flow.inject_message(flow.server_conn, 'This is an injected message!')

        self.proxy.set_addons(Inject())
        self.setup_connection()

        header, frame, _ = websocket.read_frame(self.client.rfile)
        assert header.opcode == Opcode.TEXT
        assert frame.payload == b'True'
