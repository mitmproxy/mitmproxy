import OpenSSL
import mock
import codecs

from hyperframe.frame import *

from netlib import tcp, http, utils
from netlib.tutils import raises
from netlib.exceptions import TcpDisconnect
from netlib.http.http2.connections import HTTP2Protocol, TCPHandler

from ... import tservers

class TestTCPHandlerWrapper:
    def test_wrapped(self):
        h = TCPHandler(rfile='foo', wfile='bar')
        p = HTTP2Protocol(h)
        assert p.tcp_handler.rfile == 'foo'
        assert p.tcp_handler.wfile == 'bar'

    def test_direct(self):
        p = HTTP2Protocol(rfile='foo', wfile='bar')
        assert isinstance(p.tcp_handler, TCPHandler)
        assert p.tcp_handler.rfile == 'foo'
        assert p.tcp_handler.wfile == 'bar'


class EchoHandler(tcp.BaseHandler):
    sni = None

    def handle(self):
        while True:
            v = self.rfile.safe_read(1)
            self.wfile.write(v)
            self.wfile.flush()


class TestProtocol:
    @mock.patch("netlib.http.http2.connections.HTTP2Protocol.perform_server_connection_preface")
    @mock.patch("netlib.http.http2.connections.HTTP2Protocol.perform_client_connection_preface")
    def test_perform_connection_preface(self, mock_client_method, mock_server_method):
        protocol = HTTP2Protocol(is_server=False)
        protocol.connection_preface_performed = True

        protocol.perform_connection_preface()
        assert not mock_client_method.called
        assert not mock_server_method.called

        protocol.perform_connection_preface(force=True)
        assert mock_client_method.called
        assert not mock_server_method.called

    @mock.patch("netlib.http.http2.connections.HTTP2Protocol.perform_server_connection_preface")
    @mock.patch("netlib.http.http2.connections.HTTP2Protocol.perform_client_connection_preface")
    def test_perform_connection_preface_server(self, mock_client_method, mock_server_method):
        protocol = HTTP2Protocol(is_server=True)
        protocol.connection_preface_performed = True

        protocol.perform_connection_preface()
        assert not mock_client_method.called
        assert not mock_server_method.called

        protocol.perform_connection_preface(force=True)
        assert not mock_client_method.called
        assert mock_server_method.called


class TestCheckALPNMatch(tservers.ServerTestBase):
    handler = EchoHandler
    ssl = dict(
        alpn_select=b'h2',
    )

    if tcp.HAS_ALPN:

        def test_check_alpn(self):
            c = tcp.TCPClient(("127.0.0.1", self.port))
            c.connect()
            c.convert_to_ssl(alpn_protos=[b'h2'])
            protocol = HTTP2Protocol(c)
            assert protocol.check_alpn()


class TestCheckALPNMismatch(tservers.ServerTestBase):
    handler = EchoHandler
    ssl = dict(
        alpn_select=None,
    )

    if tcp.HAS_ALPN:

        def test_check_alpn(self):
            c = tcp.TCPClient(("127.0.0.1", self.port))
            c.connect()
            c.convert_to_ssl(alpn_protos=[b'h2'])
            protocol = HTTP2Protocol(c)
            with raises(NotImplementedError):
                protocol.check_alpn()


class TestPerformServerConnectionPreface(tservers.ServerTestBase):
    class handler(tcp.BaseHandler):

        def handle(self):
            # send magic
            self.wfile.write(codecs.decode('505249202a20485454502f322e300d0a0d0a534d0d0a0d0a', 'hex_codec'))
            self.wfile.flush()

            # send empty settings frame
            self.wfile.write(codecs.decode('000000040000000000', 'hex_codec'))
            self.wfile.flush()

            # check empty settings frame
            raw = utils.http2_read_raw_frame(self.rfile)
            assert raw == codecs.decode('00000c040000000000000200000000000300000001', 'hex_codec')

            # check settings acknowledgement
            raw = utils.http2_read_raw_frame(self.rfile)
            assert raw == codecs.decode('000000040100000000', 'hex_codec')

            # send settings acknowledgement
            self.wfile.write(codecs.decode('000000040100000000', 'hex_codec'))
            self.wfile.flush()

    def test_perform_server_connection_preface(self):
        c = tcp.TCPClient(("127.0.0.1", self.port))
        c.connect()
        protocol = HTTP2Protocol(c)

        assert not protocol.connection_preface_performed
        protocol.perform_server_connection_preface()
        assert protocol.connection_preface_performed

        with raises(TcpDisconnect):
            protocol.perform_server_connection_preface(force=True)


class TestPerformClientConnectionPreface(tservers.ServerTestBase):
    class handler(tcp.BaseHandler):

        def handle(self):
            # check magic
            assert self.rfile.read(24) == HTTP2Protocol.CLIENT_CONNECTION_PREFACE

            # check empty settings frame
            assert self.rfile.read(9) ==\
                codecs.decode('000000040000000000', 'hex_codec')

            # send empty settings frame
            self.wfile.write(codecs.decode('000000040000000000', 'hex_codec'))
            self.wfile.flush()

            # check settings acknowledgement
            assert self.rfile.read(9) == \
                codecs.decode('000000040100000000', 'hex_codec')

            # send settings acknowledgement
            self.wfile.write(codecs.decode('000000040100000000', 'hex_codec'))
            self.wfile.flush()

    def test_perform_client_connection_preface(self):
        c = tcp.TCPClient(("127.0.0.1", self.port))
        c.connect()
        protocol = HTTP2Protocol(c)

        assert not protocol.connection_preface_performed
        protocol.perform_client_connection_preface()
        assert protocol.connection_preface_performed


class TestClientStreamIds(object):
    c = tcp.TCPClient(("127.0.0.1", 0))
    protocol = HTTP2Protocol(c)

    def test_client_stream_ids(self):
        assert self.protocol.current_stream_id is None
        assert self.protocol._next_stream_id() == 1
        assert self.protocol.current_stream_id == 1
        assert self.protocol._next_stream_id() == 3
        assert self.protocol.current_stream_id == 3
        assert self.protocol._next_stream_id() == 5
        assert self.protocol.current_stream_id == 5


class TestServerStreamIds(object):
    c = tcp.TCPClient(("127.0.0.1", 0))
    protocol = HTTP2Protocol(c, is_server=True)

    def test_server_stream_ids(self):
        assert self.protocol.current_stream_id is None
        assert self.protocol._next_stream_id() == 2
        assert self.protocol.current_stream_id == 2
        assert self.protocol._next_stream_id() == 4
        assert self.protocol.current_stream_id == 4
        assert self.protocol._next_stream_id() == 6
        assert self.protocol.current_stream_id == 6


class TestApplySettings(tservers.ServerTestBase):
    class handler(tcp.BaseHandler):
        def handle(self):
            # check settings acknowledgement
            assert self.rfile.read(9) == codecs.decode('000000040100000000', 'hex_codec')
            self.wfile.write("OK")
            self.wfile.flush()
            self.rfile.safe_read(9)  # just to keep the connection alive a bit longer

    ssl = True

    def test_apply_settings(self):
        c = tcp.TCPClient(("127.0.0.1", self.port))
        c.connect()
        c.convert_to_ssl()
        protocol = HTTP2Protocol(c)

        protocol._apply_settings({
            SettingsFrame.ENABLE_PUSH: 'foo',
            SettingsFrame.MAX_CONCURRENT_STREAMS: 'bar',
            SettingsFrame.INITIAL_WINDOW_SIZE: 'deadbeef',
        })

        assert c.rfile.safe_read(2) == b"OK"

        assert protocol.http2_settings[
            SettingsFrame.ENABLE_PUSH] == 'foo'
        assert protocol.http2_settings[
            SettingsFrame.MAX_CONCURRENT_STREAMS] == 'bar'
        assert protocol.http2_settings[
            SettingsFrame.INITIAL_WINDOW_SIZE] == 'deadbeef'


class TestCreateHeaders(object):
    c = tcp.TCPClient(("127.0.0.1", 0))

    def test_create_headers(self):
        headers = http.Headers([
            (b':method', b'GET'),
            (b':path', b'index.html'),
            (b':scheme', b'https'),
            (b'foo', b'bar')])

        bytes = HTTP2Protocol(self.c)._create_headers(
            headers, 1, end_stream=True)
        assert b''.join(bytes) ==\
            codecs.decode('000014010500000001824488355217caf3a69a3f87408294e7838c767f', 'hex_codec')

        bytes = HTTP2Protocol(self.c)._create_headers(
            headers, 1, end_stream=False)
        assert b''.join(bytes) ==\
            codecs.decode('000014010400000001824488355217caf3a69a3f87408294e7838c767f', 'hex_codec')

    def test_create_headers_multiple_frames(self):
        headers = http.Headers([
            (b':method', b'GET'),
            (b':path', b'/'),
            (b':scheme', b'https'),
            (b'foo', b'bar'),
            (b'server', b'version')])

        protocol = HTTP2Protocol(self.c)
        protocol.http2_settings[SettingsFrame.MAX_FRAME_SIZE] = 8
        bytes = protocol._create_headers(headers, 1, end_stream=True)
        assert len(bytes) == 3
        assert bytes[0] == codecs.decode('000008010100000001828487408294e783', 'hex_codec')
        assert bytes[1] == codecs.decode('0000080900000000018c767f7685ee5b10', 'hex_codec')
        assert bytes[2] == codecs.decode('00000209040000000163d5', 'hex_codec')


class TestCreateBody(object):
    c = tcp.TCPClient(("127.0.0.1", 0))

    def test_create_body_empty(self):
        protocol = HTTP2Protocol(self.c)
        bytes = protocol._create_body(b'', 1)
        assert b''.join(bytes) == b''

    def test_create_body_single_frame(self):
        protocol = HTTP2Protocol(self.c)
        bytes = protocol._create_body(b'foobar', 1)
        assert b''.join(bytes) == codecs.decode('000006000100000001666f6f626172', 'hex_codec')

    def test_create_body_multiple_frames(self):
        protocol = HTTP2Protocol(self.c)
        protocol.http2_settings[SettingsFrame.MAX_FRAME_SIZE] = 5
        bytes = protocol._create_body(b'foobarmehm42', 1)
        assert len(bytes) == 3
        assert bytes[0] == codecs.decode('000005000000000001666f6f6261', 'hex_codec')
        assert bytes[1] == codecs.decode('000005000000000001726d65686d', 'hex_codec')
        assert bytes[2] == codecs.decode('0000020001000000013432', 'hex_codec')


class TestReadRequest(tservers.ServerTestBase):
    class handler(tcp.BaseHandler):

        def handle(self):
            self.wfile.write(
                codecs.decode('000003010400000001828487', 'hex_codec'))
            self.wfile.write(
                codecs.decode('000006000100000001666f6f626172', 'hex_codec'))
            self.wfile.flush()
            self.rfile.safe_read(9)  # just to keep the connection alive a bit longer

    ssl = True

    def test_read_request(self):
        c = tcp.TCPClient(("127.0.0.1", self.port))
        c.connect()
        c.convert_to_ssl()
        protocol = HTTP2Protocol(c, is_server=True)
        protocol.connection_preface_performed = True

        req = protocol.read_request(NotImplemented)

        assert req.stream_id
        assert req.headers.fields == [[b':method', b'GET'], [b':path', b'/'], [b':scheme', b'https']]
        assert req.content == b'foobar'


class TestReadRequestRelative(tservers.ServerTestBase):
    class handler(tcp.BaseHandler):
        def handle(self):
            self.wfile.write(
                codecs.decode('00000c0105000000014287d5af7e4d5a777f4481f9', 'hex_codec'))
            self.wfile.flush()

    ssl = True

    def test_asterisk_form(self):
        c = tcp.TCPClient(("127.0.0.1", self.port))
        c.connect()
        c.convert_to_ssl()
        protocol = HTTP2Protocol(c, is_server=True)
        protocol.connection_preface_performed = True

        req = protocol.read_request(NotImplemented)

        assert req.first_line_format == "relative"
        assert req.method == "OPTIONS"
        assert req.path == "*"


class TestReadRequestAbsolute(tservers.ServerTestBase):
    class handler(tcp.BaseHandler):
        def handle(self):
            self.wfile.write(
                codecs.decode('00001901050000000182448d9d29aee30c0e492c2a1170426366871c92585422e085', 'hex_codec'))
            self.wfile.flush()

    ssl = True

    def test_absolute_form(self):
        c = tcp.TCPClient(("127.0.0.1", self.port))
        c.connect()
        c.convert_to_ssl()
        protocol = HTTP2Protocol(c, is_server=True)
        protocol.connection_preface_performed = True

        req = protocol.read_request(NotImplemented)

        assert req.first_line_format == "absolute"
        assert req.scheme == "http"
        assert req.host == "address"
        assert req.port == 22


class TestReadRequestConnect(tservers.ServerTestBase):
    class handler(tcp.BaseHandler):
        def handle(self):
            self.wfile.write(
                codecs.decode('00001b0105000000014287bdab4e9c17b7ff44871c92585422e08541871c92585422e085', 'hex_codec'))
            self.wfile.write(
                codecs.decode('00001d0105000000014287bdab4e9c17b7ff44882f91d35d055c87a741882f91d35d055c87a7', 'hex_codec'))
            self.wfile.flush()

    ssl = True

    def test_connect(self):
        c = tcp.TCPClient(("127.0.0.1", self.port))
        c.connect()
        c.convert_to_ssl()
        protocol = HTTP2Protocol(c, is_server=True)
        protocol.connection_preface_performed = True

        req = protocol.read_request(NotImplemented)
        assert req.first_line_format == "authority"
        assert req.method == "CONNECT"
        assert req.host == "address"
        assert req.port == 22

        req = protocol.read_request(NotImplemented)
        assert req.first_line_format == "authority"
        assert req.method == "CONNECT"
        assert req.host == "example.com"
        assert req.port == 443


class TestReadResponse(tservers.ServerTestBase):
    class handler(tcp.BaseHandler):
        def handle(self):
            self.wfile.write(
                codecs.decode('00000801040000002a88628594e78c767f', 'hex_codec'))
            self.wfile.write(
                codecs.decode('00000600010000002a666f6f626172', 'hex_codec'))
            self.wfile.flush()
            self.rfile.safe_read(9)  # just to keep the connection alive a bit longer

    ssl = True

    def test_read_response(self):
        c = tcp.TCPClient(("127.0.0.1", self.port))
        c.connect()
        c.convert_to_ssl()
        protocol = HTTP2Protocol(c)
        protocol.connection_preface_performed = True

        resp = protocol.read_response(NotImplemented, stream_id=42)

        assert resp.http_version == "HTTP/2.0"
        assert resp.status_code == 200
        assert resp.reason == ''
        assert resp.headers.fields == [[b':status', b'200'], [b'etag', b'foobar']]
        assert resp.content == b'foobar'
        assert resp.timestamp_end


class TestReadEmptyResponse(tservers.ServerTestBase):
    class handler(tcp.BaseHandler):
        def handle(self):
            self.wfile.write(
                codecs.decode('00000801050000002a88628594e78c767f', 'hex_codec'))
            self.wfile.flush()

    ssl = True

    def test_read_empty_response(self):
        c = tcp.TCPClient(("127.0.0.1", self.port))
        c.connect()
        c.convert_to_ssl()
        protocol = HTTP2Protocol(c)
        protocol.connection_preface_performed = True

        resp = protocol.read_response(NotImplemented, stream_id=42)

        assert resp.stream_id == 42
        assert resp.http_version == "HTTP/2.0"
        assert resp.status_code == 200
        assert resp.reason == ''
        assert resp.headers.fields == [[b':status', b'200'], [b'etag', b'foobar']]
        assert resp.content == b''


class TestAssembleRequest(object):
    c = tcp.TCPClient(("127.0.0.1", 0))

    def test_request_simple(self):
        bytes = HTTP2Protocol(self.c).assemble_request(http.Request(
            b'',
            b'GET',
            b'https',
            b'',
            b'',
            b'/',
            b"HTTP/2.0",
            None,
            None,
        ))
        assert len(bytes) == 1
        assert bytes[0] == codecs.decode('00000d0105000000018284874188089d5c0b8170dc07', 'hex_codec')

    def test_request_with_stream_id(self):
        req = http.Request(
            b'',
            b'GET',
            b'https',
            b'',
            b'',
            b'/',
            b"HTTP/2.0",
            None,
            None,
        )
        req.stream_id = 0x42
        bytes = HTTP2Protocol(self.c).assemble_request(req)
        assert len(bytes) == 1
        assert bytes[0] == codecs.decode('00000d0105000000428284874188089d5c0b8170dc07', 'hex_codec')

    def test_request_with_body(self):
        bytes = HTTP2Protocol(self.c).assemble_request(http.Request(
            b'',
            b'GET',
            b'https',
            b'',
            b'',
            b'/',
            b"HTTP/2.0",
            http.Headers([(b'foo', b'bar')]),
            b'foobar',
        ))
        assert len(bytes) == 2
        assert bytes[0] ==\
            codecs.decode('0000150104000000018284874188089d5c0b8170dc07408294e7838c767f', 'hex_codec')
        assert bytes[1] ==\
            codecs.decode('000006000100000001666f6f626172', 'hex_codec')


class TestAssembleResponse(object):
    c = tcp.TCPClient(("127.0.0.1", 0))

    def test_simple(self):
        bytes = HTTP2Protocol(self.c, is_server=True).assemble_response(http.Response(
            b"HTTP/2.0",
            200,
        ))
        assert len(bytes) == 1
        assert bytes[0] ==\
            codecs.decode('00000101050000000288', 'hex_codec')

    def test_with_stream_id(self):
        resp = http.Response(
            b"HTTP/2.0",
            200,
        )
        resp.stream_id = 0x42
        bytes = HTTP2Protocol(self.c, is_server=True).assemble_response(resp)
        assert len(bytes) == 1
        assert bytes[0] ==\
            codecs.decode('00000101050000004288', 'hex_codec')

    def test_with_body(self):
        bytes = HTTP2Protocol(self.c, is_server=True).assemble_response(http.Response(
            b"HTTP/2.0",
            200,
            b'',
            http.Headers(foo=b"bar"),
            b'foobar'
        ))
        assert len(bytes) == 2
        assert bytes[0] ==\
            codecs.decode('00000901040000000288408294e7838c767f', 'hex_codec')
        assert bytes[1] ==\
            codecs.decode('000006000100000002666f6f626172', 'hex_codec')
