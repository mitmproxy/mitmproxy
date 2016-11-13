import pytest
import os
import tempfile
import traceback

from mitmproxy import options
from mitmproxy import exceptions
from mitmproxy.proxy.config import ProxyConfig

import mitmproxy.net
from mitmproxy.net import http
from ...mitmproxy.net import tservers as net_tservers
from .. import tservers

from mitmproxy.net import websockets


class _WebSocketServerBase(net_tservers.ServerTestBase):

    class handler(mitmproxy.net.tcp.BaseHandler):

        def handle(self):
            try:
                request = http.http1.read_request(self.rfile)
                assert websockets.check_handshake(request.headers)

                response = http.Response(
                    "HTTP/1.1",
                    101,
                    reason=http.status_codes.RESPONSES.get(101),
                    headers=http.Headers(
                        connection='upgrade',
                        upgrade='websocket',
                        sec_websocket_accept=b'',
                    ),
                    content=b'',
                )
                self.wfile.write(http.http1.assemble_response(response))
                self.wfile.flush()

                self.server.handle_websockets(self.rfile, self.wfile)
            except:
                traceback.print_exc()


class _WebSocketTestBase:

    @classmethod
    def setup_class(cls):
        opts = cls.get_options()
        cls.config = ProxyConfig(opts)

        tmaster = tservers.TestMaster(opts, cls.config)
        cls.proxy = tservers.ProxyThread(tmaster)
        cls.proxy.start()

    @classmethod
    def teardown_class(cls):
        cls.proxy.shutdown()

    @classmethod
    def get_options(cls):
        opts = options.Options(
            listen_port=0,
            no_upstream_cert=False,
            ssl_insecure=True,
            websockets=True,
        )
        opts.cadir = os.path.join(tempfile.gettempdir(), "mitmproxy")
        return opts

    @property
    def master(self):
        return self.proxy.tmaster

    def setup(self):
        self.master.reset([])
        self.server.server.handle_websockets = self.handle_websockets

    def _setup_connection(self):
        client = mitmproxy.net.tcp.TCPClient(("127.0.0.1", self.proxy.port))
        client.connect()

        request = http.Request(
            "authority",
            "CONNECT",
            "",
            "localhost",
            self.server.server.address.port,
            "",
            "HTTP/1.1",
            content=b'')
        client.wfile.write(http.http1.assemble_request(request))
        client.wfile.flush()

        response = http.http1.read_response(client.rfile, request)

        if self.ssl:
            client.convert_to_ssl()
            assert client.ssl_established

        request = http.Request(
            "relative",
            "GET",
            "http",
            "localhost",
            self.server.server.address.port,
            "/ws",
            "HTTP/1.1",
            headers=http.Headers(
                connection="upgrade",
                upgrade="websocket",
                sec_websocket_version="13",
                sec_websocket_key="1234",
            ),
            content=b'')
        client.wfile.write(http.http1.assemble_request(request))
        client.wfile.flush()

        response = http.http1.read_response(client.rfile, request)
        assert websockets.check_handshake(response.headers)

        return client


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
        wfile.write(bytes(websockets.Frame(fin=1, opcode=websockets.OPCODE.TEXT, payload=b'server-foobar')))
        wfile.flush()

        frame = websockets.Frame.from_file(rfile)
        wfile.write(bytes(frame))
        wfile.flush()

    def test_simple(self):
        client = self._setup_connection()

        frame = websockets.Frame.from_file(client.rfile)
        assert frame.payload == b'server-foobar'

        client.wfile.write(bytes(websockets.Frame(fin=1, opcode=websockets.OPCODE.TEXT, payload=b'client-foobar')))
        client.wfile.flush()

        frame = websockets.Frame.from_file(client.rfile)
        assert frame.payload == b'client-foobar'

        client.wfile.write(bytes(websockets.Frame(fin=1, opcode=websockets.OPCODE.CLOSE)))
        client.wfile.flush()


class TestSimpleTLS(_WebSocketTest):
    ssl = True

    @classmethod
    def handle_websockets(cls, rfile, wfile):
        wfile.write(bytes(websockets.Frame(fin=1, opcode=websockets.OPCODE.TEXT, payload=b'server-foobar')))
        wfile.flush()

        frame = websockets.Frame.from_file(rfile)
        wfile.write(bytes(frame))
        wfile.flush()

    def test_simple_tls(self):
        client = self._setup_connection()

        frame = websockets.Frame.from_file(client.rfile)
        assert frame.payload == b'server-foobar'

        client.wfile.write(bytes(websockets.Frame(fin=1, opcode=websockets.OPCODE.TEXT, payload=b'client-foobar')))
        client.wfile.flush()

        frame = websockets.Frame.from_file(client.rfile)
        assert frame.payload == b'client-foobar'

        client.wfile.write(bytes(websockets.Frame(fin=1, opcode=websockets.OPCODE.CLOSE)))
        client.wfile.flush()


class TestPing(_WebSocketTest):

    @classmethod
    def handle_websockets(cls, rfile, wfile):
        wfile.write(bytes(websockets.Frame(fin=1, opcode=websockets.OPCODE.PING, payload=b'foobar')))
        wfile.flush()

        frame = websockets.Frame.from_file(rfile)
        assert frame.header.opcode == websockets.OPCODE.PONG
        assert frame.payload == b'foobar'

        wfile.write(bytes(websockets.Frame(fin=1, opcode=websockets.OPCODE.TEXT, payload=b'pong-received')))
        wfile.flush()

    def test_ping(self):
        client = self._setup_connection()

        frame = websockets.Frame.from_file(client.rfile)
        assert frame.header.opcode == websockets.OPCODE.PING
        assert frame.payload == b'foobar'

        client.wfile.write(bytes(websockets.Frame(fin=1, opcode=websockets.OPCODE.PONG, payload=frame.payload)))
        client.wfile.flush()

        frame = websockets.Frame.from_file(client.rfile)
        assert frame.header.opcode == websockets.OPCODE.TEXT
        assert frame.payload == b'pong-received'


class TestPong(_WebSocketTest):

    @classmethod
    def handle_websockets(cls, rfile, wfile):
        frame = websockets.Frame.from_file(rfile)
        assert frame.header.opcode == websockets.OPCODE.PING
        assert frame.payload == b'foobar'

        wfile.write(bytes(websockets.Frame(fin=1, opcode=websockets.OPCODE.PONG, payload=frame.payload)))
        wfile.flush()

    def test_pong(self):
        client = self._setup_connection()

        client.wfile.write(bytes(websockets.Frame(fin=1, opcode=websockets.OPCODE.PING, payload=b'foobar')))
        client.wfile.flush()

        frame = websockets.Frame.from_file(client.rfile)
        assert frame.header.opcode == websockets.OPCODE.PONG
        assert frame.payload == b'foobar'


class TestClose(_WebSocketTest):

    @classmethod
    def handle_websockets(cls, rfile, wfile):
        frame = websockets.Frame.from_file(rfile)
        wfile.write(bytes(frame))
        wfile.flush()

        with pytest.raises(exceptions.TcpDisconnect):
            websockets.Frame.from_file(rfile)

    def test_close(self):
        client = self._setup_connection()

        client.wfile.write(bytes(websockets.Frame(fin=1, opcode=websockets.OPCODE.CLOSE)))
        client.wfile.flush()

        with pytest.raises(exceptions.TcpDisconnect):
            websockets.Frame.from_file(client.rfile)

    def test_close_payload_1(self):
        client = self._setup_connection()

        client.wfile.write(bytes(websockets.Frame(fin=1, opcode=websockets.OPCODE.CLOSE, payload=b'\00\42')))
        client.wfile.flush()

        with pytest.raises(exceptions.TcpDisconnect):
            websockets.Frame.from_file(client.rfile)

    def test_close_payload_2(self):
        client = self._setup_connection()

        client.wfile.write(bytes(websockets.Frame(fin=1, opcode=websockets.OPCODE.CLOSE, payload=b'\00\42foobar')))
        client.wfile.flush()

        with pytest.raises(exceptions.TcpDisconnect):
            websockets.Frame.from_file(client.rfile)


class TestInvalidFrame(_WebSocketTest):

    @classmethod
    def handle_websockets(cls, rfile, wfile):
        wfile.write(bytes(websockets.Frame(fin=1, opcode=15, payload=b'foobar')))
        wfile.flush()

    def test_invalid_frame(self):
        client = self._setup_connection()

        # with pytest.raises(exceptions.TcpDisconnect):
        frame = websockets.Frame.from_file(client.rfile)
        assert frame.header.opcode == 15
        assert frame.payload == b'foobar'
