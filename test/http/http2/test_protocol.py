import OpenSSL
import mock

from netlib import tcp, odict, http, tutils
from netlib.http import http2
from netlib.http.http2 import HTTP2Protocol
from netlib.http.http2.frame import *
from ... import tservers

class TestTCPHandlerWrapper:
    def test_wrapped(self):
        h = http2.TCPHandler(rfile='foo', wfile='bar')
        p = HTTP2Protocol(h)
        assert p.tcp_handler.rfile == 'foo'
        assert p.tcp_handler.wfile == 'bar'

    def test_direct(self):
        p = HTTP2Protocol(rfile='foo', wfile='bar')
        assert isinstance(p.tcp_handler, http2.TCPHandler)
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
    @mock.patch("netlib.http.http2.HTTP2Protocol.perform_server_connection_preface")
    @mock.patch("netlib.http.http2.HTTP2Protocol.perform_client_connection_preface")
    def test_perform_connection_preface(self, mock_client_method, mock_server_method):
        protocol = HTTP2Protocol(is_server=False)
        protocol.connection_preface_performed = True

        protocol.perform_connection_preface()
        assert not mock_client_method.called
        assert not mock_server_method.called

        protocol.perform_connection_preface(force=True)
        assert mock_client_method.called
        assert not mock_server_method.called

    @mock.patch("netlib.http.http2.HTTP2Protocol.perform_server_connection_preface")
    @mock.patch("netlib.http.http2.HTTP2Protocol.perform_client_connection_preface")
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
        alpn_select=HTTP2Protocol.ALPN_PROTO_H2,
    )

    if OpenSSL._util.lib.Cryptography_HAS_ALPN:

        def test_check_alpn(self):
            c = tcp.TCPClient(("127.0.0.1", self.port))
            c.connect()
            c.convert_to_ssl(alpn_protos=[HTTP2Protocol.ALPN_PROTO_H2])
            protocol = HTTP2Protocol(c)
            assert protocol.check_alpn()


class TestCheckALPNMismatch(tservers.ServerTestBase):
    handler = EchoHandler
    ssl = dict(
        alpn_select=None,
    )

    if OpenSSL._util.lib.Cryptography_HAS_ALPN:

        def test_check_alpn(self):
            c = tcp.TCPClient(("127.0.0.1", self.port))
            c.connect()
            c.convert_to_ssl(alpn_protos=[HTTP2Protocol.ALPN_PROTO_H2])
            protocol = HTTP2Protocol(c)
            tutils.raises(NotImplementedError, protocol.check_alpn)


class TestPerformServerConnectionPreface(tservers.ServerTestBase):
    class handler(tcp.BaseHandler):

        def handle(self):
            # send magic
            self.wfile.write(
                '505249202a20485454502f322e300d0a0d0a534d0d0a0d0a'.decode('hex'))
            self.wfile.flush()

            # send empty settings frame
            self.wfile.write('000000040000000000'.decode('hex'))
            self.wfile.flush()

            # check empty settings frame
            assert self.rfile.read(9) ==\
                '000000040000000000'.decode('hex')

            # check settings acknowledgement
            assert self.rfile.read(9) == \
                '000000040100000000'.decode('hex')

            # send settings acknowledgement
            self.wfile.write('000000040100000000'.decode('hex'))
            self.wfile.flush()

    def test_perform_server_connection_preface(self):
        c = tcp.TCPClient(("127.0.0.1", self.port))
        c.connect()
        protocol = HTTP2Protocol(c)

        assert not protocol.connection_preface_performed
        protocol.perform_server_connection_preface()
        assert protocol.connection_preface_performed

        tutils.raises(tcp.NetLibDisconnect, protocol.perform_server_connection_preface, force=True)


class TestPerformClientConnectionPreface(tservers.ServerTestBase):
    class handler(tcp.BaseHandler):

        def handle(self):
            # check magic
            assert self.rfile.read(24) ==\
                '505249202a20485454502f322e300d0a0d0a534d0d0a0d0a'.decode('hex')

            # check empty settings frame
            assert self.rfile.read(9) ==\
                '000000040000000000'.decode('hex')

            # send empty settings frame
            self.wfile.write('000000040000000000'.decode('hex'))
            self.wfile.flush()

            # check settings acknowledgement
            assert self.rfile.read(9) == \
                '000000040100000000'.decode('hex')

            # send settings acknowledgement
            self.wfile.write('000000040100000000'.decode('hex'))
            self.wfile.flush()

    def test_perform_client_connection_preface(self):
        c = tcp.TCPClient(("127.0.0.1", self.port))
        c.connect()
        protocol = HTTP2Protocol(c)

        assert not protocol.connection_preface_performed
        protocol.perform_client_connection_preface()
        assert protocol.connection_preface_performed


class TestClientStreamIds():
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


class TestServerStreamIds():
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
            assert self.rfile.read(9) == '000000040100000000'.decode('hex')
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
            SettingsFrame.SETTINGS.SETTINGS_ENABLE_PUSH: 'foo',
            SettingsFrame.SETTINGS.SETTINGS_MAX_CONCURRENT_STREAMS: 'bar',
            SettingsFrame.SETTINGS.SETTINGS_INITIAL_WINDOW_SIZE: 'deadbeef',
        })

        assert c.rfile.safe_read(2) == "OK"

        assert protocol.http2_settings[
            SettingsFrame.SETTINGS.SETTINGS_ENABLE_PUSH] == 'foo'
        assert protocol.http2_settings[
            SettingsFrame.SETTINGS.SETTINGS_MAX_CONCURRENT_STREAMS] == 'bar'
        assert protocol.http2_settings[
            SettingsFrame.SETTINGS.SETTINGS_INITIAL_WINDOW_SIZE] == 'deadbeef'


class TestCreateHeaders():
    c = tcp.TCPClient(("127.0.0.1", 0))

    def test_create_headers(self):
        headers = [
            (b':method', b'GET'),
            (b':path', b'index.html'),
            (b':scheme', b'https'),
            (b'foo', b'bar')]

        bytes = HTTP2Protocol(self.c)._create_headers(
            headers, 1, end_stream=True)
        assert b''.join(bytes) ==\
            '000014010500000001824488355217caf3a69a3f87408294e7838c767f'\
            .decode('hex')

        bytes = HTTP2Protocol(self.c)._create_headers(
            headers, 1, end_stream=False)
        assert b''.join(bytes) ==\
            '000014010400000001824488355217caf3a69a3f87408294e7838c767f'\
            .decode('hex')

    def test_create_headers_multiple_frames(self):
        headers = [
            (b':method', b'GET'),
            (b':path', b'/'),
            (b':scheme', b'https'),
            (b'foo', b'bar'),
            (b'server', b'version')]

        protocol = HTTP2Protocol(self.c)
        protocol.http2_settings[SettingsFrame.SETTINGS.SETTINGS_MAX_FRAME_SIZE] = 8
        bytes = protocol._create_headers(headers, 1, end_stream=True)
        assert len(bytes) == 3
        assert bytes[0] == '000008010000000001828487408294e783'.decode('hex')
        assert bytes[1] == '0000080900000000018c767f7685ee5b10'.decode('hex')
        assert bytes[2] == '00000209050000000163d5'.decode('hex')


class TestCreateBody():
    c = tcp.TCPClient(("127.0.0.1", 0))

    def test_create_body_empty(self):
        protocol = HTTP2Protocol(self.c)
        bytes = protocol._create_body(b'', 1)
        assert b''.join(bytes) == ''.decode('hex')

    def test_create_body_single_frame(self):
        protocol = HTTP2Protocol(self.c)
        bytes = protocol._create_body('foobar', 1)
        assert b''.join(bytes) == '000006000100000001666f6f626172'.decode('hex')

    def test_create_body_multiple_frames(self):
        protocol = HTTP2Protocol(self.c)
        protocol.http2_settings[SettingsFrame.SETTINGS.SETTINGS_MAX_FRAME_SIZE] = 5
        bytes = protocol._create_body('foobarmehm42', 1)
        assert len(bytes) == 3
        assert bytes[0] == '000005000000000001666f6f6261'.decode('hex')
        assert bytes[1] == '000005000000000001726d65686d'.decode('hex')
        assert bytes[2] == '0000020001000000013432'.decode('hex')


class TestReadRequest(tservers.ServerTestBase):
    class handler(tcp.BaseHandler):
        def handle(self):
            self.wfile.write(
                b'000003010400000001828487'.decode('hex'))
            self.wfile.write(
                b'000006000100000001666f6f626172'.decode('hex'))
            self.wfile.flush()
            self.rfile.safe_read(9)  # just to keep the connection alive a bit longer

    ssl = True

    def test_read_request(self):
        c = tcp.TCPClient(("127.0.0.1", self.port))
        c.connect()
        c.convert_to_ssl()
        protocol = HTTP2Protocol(c, is_server=True)
        protocol.connection_preface_performed = True

        req = protocol.read_request()

        assert req.stream_id
        assert req.headers.lst == [[u':method', u'GET'], [u':path', u'/'], [u':scheme', u'https']]
        assert req.body == b'foobar'


class TestReadRequestRelative(tservers.ServerTestBase):
    class handler(tcp.BaseHandler):
        def handle(self):
            self.wfile.write(
                b'00000c0105000000014287d5af7e4d5a777f4481f9'.decode('hex'))
            self.wfile.flush()

    ssl = True

    def test_asterisk_form_in(self):
        c = tcp.TCPClient(("127.0.0.1", self.port))
        c.connect()
        c.convert_to_ssl()
        protocol = HTTP2Protocol(c, is_server=True)
        protocol.connection_preface_performed = True

        req = protocol.read_request()

        assert req.form_in == "relative"
        assert req.method == "OPTIONS"
        assert req.path == "*"


class TestReadRequestAbsolute(tservers.ServerTestBase):
    class handler(tcp.BaseHandler):
        def handle(self):
            self.wfile.write(
                b'00001901050000000182448d9d29aee30c0e492c2a1170426366871c92585422e085'.decode('hex'))
            self.wfile.flush()

    ssl = True

    def test_absolute_form_in(self):
        c = tcp.TCPClient(("127.0.0.1", self.port))
        c.connect()
        c.convert_to_ssl()
        protocol = HTTP2Protocol(c, is_server=True)
        protocol.connection_preface_performed = True

        req = protocol.read_request()

        assert req.form_in == "absolute"
        assert req.scheme == "http"
        assert req.host == "address"
        assert req.port == 22


class TestReadRequestConnect(tservers.ServerTestBase):
    class handler(tcp.BaseHandler):
        def handle(self):
            self.wfile.write(
                b'00001b0105000000014287bdab4e9c17b7ff44871c92585422e08541871c92585422e085'.decode('hex'))
            self.wfile.flush()

    ssl = True

    def test_connect(self):
        c = tcp.TCPClient(("127.0.0.1", self.port))
        c.connect()
        c.convert_to_ssl()
        protocol = HTTP2Protocol(c, is_server=True)
        protocol.connection_preface_performed = True

        req = protocol.read_request()

        assert req.form_in == "authority"
        assert req.method == "CONNECT"
        assert req.host == "address"
        assert req.port == 22


class TestReadResponse(tservers.ServerTestBase):
    class handler(tcp.BaseHandler):
        def handle(self):
            self.wfile.write(
                b'00000801040000000188628594e78c767f'.decode('hex'))
            self.wfile.write(
                b'000006000100000001666f6f626172'.decode('hex'))
            self.wfile.flush()
            self.rfile.safe_read(9)  # just to keep the connection alive a bit longer

    ssl = True

    def test_read_response(self):
        c = tcp.TCPClient(("127.0.0.1", self.port))
        c.connect()
        c.convert_to_ssl()
        protocol = HTTP2Protocol(c)
        protocol.connection_preface_performed = True

        resp = protocol.read_response()

        assert resp.httpversion == (2, 0)
        assert resp.status_code == 200
        assert resp.msg == ""
        assert resp.headers.lst == [[':status', '200'], ['etag', 'foobar']]
        assert resp.body == b'foobar'
        assert resp.timestamp_end

    def test_read_response_no_body(self):
        c = tcp.TCPClient(("127.0.0.1", self.port))
        c.connect()
        c.convert_to_ssl()
        protocol = HTTP2Protocol(c)
        protocol.connection_preface_performed = True

        resp = protocol.read_response(include_body=False)

        assert resp.httpversion == (2, 0)
        assert resp.status_code == 200
        assert resp.msg == ""
        assert resp.headers.lst == [[':status', '200'], ['etag', 'foobar']]
        assert resp.body == b'foobar'  # TODO: this should be true: assert resp.body == http.CONTENT_MISSING
        assert not resp.timestamp_end


class TestReadEmptyResponse(tservers.ServerTestBase):
    class handler(tcp.BaseHandler):

        def handle(self):
            self.wfile.write(
                b'00000801050000000188628594e78c767f'.decode('hex'))
            self.wfile.flush()

    ssl = True

    def test_read_empty_response(self):
        c = tcp.TCPClient(("127.0.0.1", self.port))
        c.connect()
        c.convert_to_ssl()
        protocol = HTTP2Protocol(c)
        protocol.connection_preface_performed = True

        resp = protocol.read_response()

        assert resp.stream_id
        assert resp.httpversion == (2, 0)
        assert resp.status_code == 200
        assert resp.msg == ""
        assert resp.headers.lst == [[':status', '200'], ['etag', 'foobar']]
        assert resp.body == b''


class TestAssembleRequest(object):
    c = tcp.TCPClient(("127.0.0.1", 0))

    def test_request_simple(self):
        bytes = HTTP2Protocol(self.c).assemble_request(http.Request(
            '',
            'GET',
            'https',
            '',
            '',
            '/',
            (2, 0),
            None,
            None,
        ))
        assert len(bytes) == 1
        assert bytes[0] == '00000d0105000000018284874188089d5c0b8170dc07'.decode('hex')

    def test_request_with_stream_id(self):
        req = http.Request(
            '',
            'GET',
            'https',
            '',
            '',
            '/',
            (2, 0),
            None,
            None,
        )
        req.stream_id = 0x42
        bytes = HTTP2Protocol(self.c).assemble_request(req)
        assert len(bytes) == 1
        assert bytes[0] == '00000d0105000000428284874188089d5c0b8170dc07'.decode('hex')

    def test_request_with_body(self):
        bytes = HTTP2Protocol(self.c).assemble_request(http.Request(
            '',
            'GET',
            'https',
            '',
            '',
            '/',
            (2, 0),
            odict.ODictCaseless([('foo', 'bar')]),
            'foobar',
        ))
        assert len(bytes) == 2
        assert bytes[0] ==\
            '0000150104000000018284874188089d5c0b8170dc07408294e7838c767f'.decode('hex')
        assert bytes[1] ==\
            '000006000100000001666f6f626172'.decode('hex')


class TestAssembleResponse(object):
    c = tcp.TCPClient(("127.0.0.1", 0))

    def test_simple(self):
        bytes = HTTP2Protocol(self.c, is_server=True).assemble_response(http.Response(
            (2, 0),
            200,
        ))
        assert len(bytes) == 1
        assert bytes[0] ==\
            '00000101050000000288'.decode('hex')

    def test_with_stream_id(self):
        resp = http.Response(
            (2, 0),
            200,
        )
        resp.stream_id = 0x42
        bytes = HTTP2Protocol(self.c, is_server=True).assemble_response(resp)
        assert len(bytes) == 1
        assert bytes[0] ==\
            '00000101050000004288'.decode('hex')

    def test_with_body(self):
        bytes = HTTP2Protocol(self.c, is_server=True).assemble_response(http.Response(
            (2, 0),
            200,
            '',
            odict.ODictCaseless([('foo', 'bar')]),
            'foobar'
        ))
        assert len(bytes) == 2
        assert bytes[0] ==\
            '00000901040000000288408294e7838c767f'.decode('hex')
        assert bytes[1] ==\
            '000006000100000002666f6f626172'.decode('hex')
