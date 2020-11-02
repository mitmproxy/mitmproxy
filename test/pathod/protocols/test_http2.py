from unittest import mock

import hyperframe
import pytest

from mitmproxy import exceptions
from mitmproxy.net import http, tcp
from mitmproxy.net.http import http2
from pathod.protocols.http2 import HTTP2StateProtocol, TCPHandler
from ...mitmproxy.net import tservers as net_tservers


class TestTCPHandlerWrapper:
    def test_wrapped(self):
        h = TCPHandler(rfile='foo', wfile='bar')
        p = HTTP2StateProtocol(h)
        assert p.tcp_handler.rfile == 'foo'
        assert p.tcp_handler.wfile == 'bar'

    def test_direct(self):
        p = HTTP2StateProtocol(rfile='foo', wfile='bar')
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
    @mock.patch("pathod.protocols.http2.HTTP2StateProtocol.perform_server_connection_preface")
    @mock.patch("pathod.protocols.http2.HTTP2StateProtocol.perform_client_connection_preface")
    def test_perform_connection_preface(self, mock_client_method, mock_server_method):
        protocol = HTTP2StateProtocol(is_server=False)
        protocol.connection_preface_performed = True

        protocol.perform_connection_preface()
        assert not mock_client_method.called
        assert not mock_server_method.called

        protocol.perform_connection_preface(force=True)
        assert mock_client_method.called
        assert not mock_server_method.called

    @mock.patch("pathod.protocols.http2.HTTP2StateProtocol.perform_server_connection_preface")
    @mock.patch("pathod.protocols.http2.HTTP2StateProtocol.perform_client_connection_preface")
    def test_perform_connection_preface_server(self, mock_client_method, mock_server_method):
        protocol = HTTP2StateProtocol(is_server=True)
        protocol.connection_preface_performed = True

        protocol.perform_connection_preface()
        assert not mock_client_method.called
        assert not mock_server_method.called

        protocol.perform_connection_preface(force=True)
        assert not mock_client_method.called
        assert mock_server_method.called


class TestCheckALPNMatch(net_tservers.ServerTestBase):
    handler = EchoHandler
    ssl = dict(
        alpn_select=b'h2',
    )

    def test_check_alpn(self):
        c = tcp.TCPClient(("127.0.0.1", self.port))
        with c.connect():
            c.convert_to_tls(alpn_protos=[b'h2'])
            protocol = HTTP2StateProtocol(c)
            assert protocol.check_alpn()


class TestCheckALPNMismatch(net_tservers.ServerTestBase):
    handler = EchoHandler
    ssl = dict(
        alpn_select=None,
    )

    def test_check_alpn(self):
        c = tcp.TCPClient(("127.0.0.1", self.port))
        with c.connect():
            c.convert_to_tls(alpn_protos=[b'h2'])
            protocol = HTTP2StateProtocol(c)
            with pytest.raises(NotImplementedError):
                protocol.check_alpn()


class TestPerformServerConnectionPreface(net_tservers.ServerTestBase):
    class handler(tcp.BaseHandler):

        def handle(self):
            # send magic
            self.wfile.write(bytes.fromhex("505249202a20485454502f322e300d0a0d0a534d0d0a0d0a"))
            self.wfile.flush()

            # send empty settings frame
            self.wfile.write(bytes.fromhex("000000040000000000"))
            self.wfile.flush()

            # check empty settings frame
            _, consumed_bytes = http2.read_frame(self.rfile, False)
            assert consumed_bytes == bytes.fromhex("00000c040000000000000200000000000300000001")

            # check settings acknowledgement
            _, consumed_bytes = http2.read_frame(self.rfile, False)
            assert consumed_bytes == bytes.fromhex("000000040100000000")

            # send settings acknowledgement
            self.wfile.write(bytes.fromhex("000000040100000000"))
            self.wfile.flush()

    def test_perform_server_connection_preface(self):
        c = tcp.TCPClient(("127.0.0.1", self.port))
        with c.connect():
            protocol = HTTP2StateProtocol(c)

            assert not protocol.connection_preface_performed
            protocol.perform_server_connection_preface()
            assert protocol.connection_preface_performed

            with pytest.raises(exceptions.TcpReadIncomplete):
                protocol.perform_server_connection_preface(force=True)


class TestPerformClientConnectionPreface(net_tservers.ServerTestBase):
    class handler(tcp.BaseHandler):

        def handle(self):
            # check magic
            assert self.rfile.read(24) == HTTP2StateProtocol.CLIENT_CONNECTION_PREFACE

            # check empty settings frame
            assert self.rfile.read(9) ==\
                bytes.fromhex("000000040000000000")

            # send empty settings frame
            self.wfile.write(bytes.fromhex("000000040000000000"))
            self.wfile.flush()

            # check settings acknowledgement
            assert self.rfile.read(9) == \
                bytes.fromhex("000000040100000000")

            # send settings acknowledgement
            self.wfile.write(bytes.fromhex("000000040100000000"))
            self.wfile.flush()

    def test_perform_client_connection_preface(self):
        c = tcp.TCPClient(("127.0.0.1", self.port))
        with c.connect():
            protocol = HTTP2StateProtocol(c)

            assert not protocol.connection_preface_performed
            protocol.perform_client_connection_preface()
            assert protocol.connection_preface_performed


class TestClientStreamIds:
    c = tcp.TCPClient(("127.0.0.1", 0))
    protocol = HTTP2StateProtocol(c)

    def test_client_stream_ids(self):
        assert self.protocol.current_stream_id is None
        assert self.protocol._next_stream_id() == 1
        assert self.protocol.current_stream_id == 1
        assert self.protocol._next_stream_id() == 3
        assert self.protocol.current_stream_id == 3
        assert self.protocol._next_stream_id() == 5
        assert self.protocol.current_stream_id == 5


class TestserverstreamIds:
    c = tcp.TCPClient(("127.0.0.1", 0))
    protocol = HTTP2StateProtocol(c, is_server=True)

    def test_server_stream_ids(self):
        assert self.protocol.current_stream_id is None
        assert self.protocol._next_stream_id() == 2
        assert self.protocol.current_stream_id == 2
        assert self.protocol._next_stream_id() == 4
        assert self.protocol.current_stream_id == 4
        assert self.protocol._next_stream_id() == 6
        assert self.protocol.current_stream_id == 6


class TestApplySettings(net_tservers.ServerTestBase):
    class handler(tcp.BaseHandler):
        def handle(self):
            # check settings acknowledgement
            assert self.rfile.read(9) == bytes.fromhex("000000040100000000")
            self.wfile.write(b"OK")
            self.wfile.flush()
            self.rfile.safe_read(9)  # just to keep the connection alive a bit longer

    ssl = True

    def test_apply_settings(self):
        c = tcp.TCPClient(("127.0.0.1", self.port))
        with c.connect():
            c.convert_to_tls()
            protocol = HTTP2StateProtocol(c)

            protocol._apply_settings({
                hyperframe.frame.SettingsFrame.ENABLE_PUSH: 'foo',
                hyperframe.frame.SettingsFrame.MAX_CONCURRENT_STREAMS: 'bar',
                hyperframe.frame.SettingsFrame.INITIAL_WINDOW_SIZE: 'deadbeef',
            })

            assert c.rfile.safe_read(2) == b"OK"

            assert protocol.http2_settings[
                hyperframe.frame.SettingsFrame.ENABLE_PUSH] == 'foo'
            assert protocol.http2_settings[
                hyperframe.frame.SettingsFrame.MAX_CONCURRENT_STREAMS] == 'bar'
            assert protocol.http2_settings[
                hyperframe.frame.SettingsFrame.INITIAL_WINDOW_SIZE] == 'deadbeef'


class TestCreateHeaders:
    c = tcp.TCPClient(("127.0.0.1", 0))

    def test_create_headers(self):
        headers = http.Headers([
            (b':method', b'GET'),
            (b':path', b'index.html'),
            (b':scheme', b'https'),
            (b'foo', b'bar')])

        data = HTTP2StateProtocol(self.c)._create_headers(
            headers, 1, end_stream=True)
        assert b''.join(data) == bytes.fromhex("000014010500000001824488355217caf3a69a3f87408294e7838c767f")

        data = HTTP2StateProtocol(self.c)._create_headers(
            headers, 1, end_stream=False)
        assert b''.join(data) == bytes.fromhex("000014010400000001824488355217caf3a69a3f87408294e7838c767f")

    def test_create_headers_multiple_frames(self):
        headers = http.Headers([
            (b':method', b'GET'),
            (b':path', b'/'),
            (b':scheme', b'https'),
            (b'foo', b'bar'),
            (b'server', b'version')])

        protocol = HTTP2StateProtocol(self.c)
        protocol.http2_settings[hyperframe.frame.SettingsFrame.MAX_FRAME_SIZE] = 8
        data = protocol._create_headers(headers, 1, end_stream=True)
        assert len(data) == 3
        assert data[0] == bytes.fromhex("000008010100000001828487408294e783")
        assert data[1] == bytes.fromhex("0000080900000000018c767f7685ee5b10")
        assert data[2] == bytes.fromhex("00000209040000000163d5")


class TestCreateBody:
    c = tcp.TCPClient(("127.0.0.1", 0))

    def test_create_body_empty(self):
        protocol = HTTP2StateProtocol(self.c)
        bytes = protocol._create_body(b'', 1)
        assert b''.join(bytes) == b''

    def test_create_body_single_frame(self):
        protocol = HTTP2StateProtocol(self.c)
        data = protocol._create_body(b'foobar', 1)
        assert b''.join(data) == bytes.fromhex("000006000100000001666f6f626172")

    def test_create_body_multiple_frames(self):
        protocol = HTTP2StateProtocol(self.c)
        protocol.http2_settings[hyperframe.frame.SettingsFrame.MAX_FRAME_SIZE] = 5
        data = protocol._create_body(b'foobarmehm42', 1)
        assert len(data) == 3
        assert data[0] == bytes.fromhex("000005000000000001666f6f6261")
        assert data[1] == bytes.fromhex("000005000000000001726d65686d")
        assert data[2] == bytes.fromhex("0000020001000000013432")


class TestReadRequest(net_tservers.ServerTestBase):
    class handler(tcp.BaseHandler):

        def handle(self):
            self.wfile.write(
                bytes.fromhex("000003010400000001828487"))
            self.wfile.write(
                bytes.fromhex("000006000100000001666f6f626172"))
            self.wfile.flush()
            self.rfile.safe_read(9)  # just to keep the connection alive a bit longer

    ssl = True

    def test_read_request(self):
        c = tcp.TCPClient(("127.0.0.1", self.port))
        with c.connect():
            c.convert_to_tls()
            protocol = HTTP2StateProtocol(c, is_server=True)
            protocol.connection_preface_performed = True

            req = protocol.read_request(NotImplemented)

            assert req.stream_id
            assert req.headers.fields == ()
            assert req.method == "GET"
            assert req.path == "/"
            assert req.scheme == "https"
            assert req.content == b'foobar'


class TestReadRequestRelative(net_tservers.ServerTestBase):
    class handler(tcp.BaseHandler):
        def handle(self):
            self.wfile.write(
                bytes.fromhex("00000c0105000000014287d5af7e4d5a777f4481f9"))
            self.wfile.flush()

    ssl = True

    def test_asterisk_form(self):
        c = tcp.TCPClient(("127.0.0.1", self.port))
        with c.connect():
            c.convert_to_tls()
            protocol = HTTP2StateProtocol(c, is_server=True)
            protocol.connection_preface_performed = True

            req = protocol.read_request(NotImplemented)

            assert req.first_line_format == "relative"
            assert req.method == "OPTIONS"
            assert req.path == "*"


class TestReadResponse(net_tservers.ServerTestBase):
    class handler(tcp.BaseHandler):
        def handle(self):
            self.wfile.write(
                bytes.fromhex("00000801040000002a88628594e78c767f"))
            self.wfile.write(
                bytes.fromhex("00000600010000002a666f6f626172"))
            self.wfile.flush()
            self.rfile.safe_read(9)  # just to keep the connection alive a bit longer

    ssl = True

    def test_read_response(self):
        c = tcp.TCPClient(("127.0.0.1", self.port))
        with c.connect():
            c.convert_to_tls()
            protocol = HTTP2StateProtocol(c)
            protocol.connection_preface_performed = True

            resp = protocol.read_response(NotImplemented, stream_id=42)

            assert resp.http_version == "HTTP/2.0"
            assert resp.status_code == 200
            assert resp.reason == ''
            assert resp.headers.fields == ((b':status', b'200'), (b'etag', b'foobar'))
            assert resp.content == b'foobar'
            assert resp.timestamp_end


class TestReadEmptyResponse(net_tservers.ServerTestBase):
    class handler(tcp.BaseHandler):
        def handle(self):
            self.wfile.write(
                bytes.fromhex("00000801050000002a88628594e78c767f"))
            self.wfile.flush()

    ssl = True

    def test_read_empty_response(self):
        c = tcp.TCPClient(("127.0.0.1", self.port))
        with c.connect():
            c.convert_to_tls()
            protocol = HTTP2StateProtocol(c)
            protocol.connection_preface_performed = True

            resp = protocol.read_response(NotImplemented, stream_id=42)

            assert resp.stream_id == 42
            assert resp.http_version == "HTTP/2.0"
            assert resp.status_code == 200
            assert resp.reason == ''
            assert resp.headers.fields == ((b':status', b'200'), (b'etag', b'foobar'))
            assert resp.content == b''


class TestAssembleRequest:
    c = tcp.TCPClient(("127.0.0.1", 0))

    def test_request_simple(self):
        data = HTTP2StateProtocol(self.c).assemble_request(http.Request(
            host="",
            port=0,
            method=b'GET',
            scheme=b'https',
            authority=b'',
            path=b'/',
            http_version=b"HTTP/2.0",
            headers=(),
            content=None,
            trailers=None,
            timestamp_start=0,
            timestamp_end=0
        ))
        assert len(data) == 1
        assert data[0] == bytes.fromhex('00000d0105000000018284874188089d5c0b8170dc07')

    def test_request_with_stream_id(self):
        req = http.Request(
            host="",
            port=0,
            method=b'GET',
            scheme=b'https',
            authority=b'',
            path=b'/',
            http_version=b"HTTP/2.0",
            headers=(),
            content=None,
            trailers=None,
            timestamp_start=0,
            timestamp_end=0
        )
        req.stream_id = 0x42
        data = HTTP2StateProtocol(self.c).assemble_request(req)
        assert len(data) == 1
        assert data[0] == bytes.fromhex('00000d0105000000428284874188089d5c0b8170dc07')

    def test_request_with_body(self):
        data = HTTP2StateProtocol(self.c).assemble_request(http.Request(
            host="",
            port=0,
            method=b'GET',
            scheme=b'https',
            authority=b'',
            path=b'/',
            http_version=b"HTTP/2.0",
            headers=http.Headers([(b'foo', b'bar')]),
            content=b'foobar',
            trailers=None,
            timestamp_start=0,
            timestamp_end=None,
        ))
        assert len(data) == 2
        assert data[0] == bytes.fromhex("0000150104000000018284874188089d5c0b8170dc07408294e7838c767f")
        assert data[1] == bytes.fromhex("000006000100000001666f6f626172")


class TestAssembleResponse:
    c = tcp.TCPClient(("127.0.0.1", 0))

    def test_simple(self):
        data = HTTP2StateProtocol(self.c, is_server=True).assemble_response(http.Response(
            http_version=b"HTTP/2.0",
            status_code=200,
            reason=b"",
            headers=(),
            content=b"",
            trailers=None,
            timestamp_start=0,
            timestamp_end=0,
        ))
        assert len(data) == 1
        assert data[0] == bytes.fromhex("00000101050000000288")

    def test_with_stream_id(self):
        resp = http.Response(
            http_version=b"HTTP/2.0",
            status_code=200,
            reason=b"",
            headers=(),
            content=b"",
            trailers=None,
            timestamp_start=0,
            timestamp_end=0,
        )
        resp.stream_id = 0x42
        data = HTTP2StateProtocol(self.c, is_server=True).assemble_response(resp)
        assert len(data) == 1
        assert data[0] == bytes.fromhex("00000101050000004288")

    def test_with_body(self):
        data = HTTP2StateProtocol(self.c, is_server=True).assemble_response(http.Response(
            http_version=b"HTTP/2.0",
            status_code=200,
            reason=b'',
            headers=http.Headers(foo=b"bar"),
            content=b'foobar',
            trailers=None,
            timestamp_start=0,
            timestamp_end=0,
        ))
        assert len(data) == 2
        assert data[0] == bytes.fromhex("00000901040000000288408294e7838c767f")
        assert data[1] == bytes.fromhex("000006000100000002666f6f626172")
