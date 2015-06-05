
import OpenSSL

from netlib import http2
from netlib import tcp
from netlib import test
from netlib.http2.frame import *
from test import tutils


class EchoHandler(tcp.BaseHandler):
    sni = None

    def handle(self):
        v = self.rfile.readline()
        self.wfile.write(v)
        self.wfile.flush()


class TestCheckALPNMatch(test.ServerTestBase):
    handler = EchoHandler
    ssl = dict(
        alpn_select=http2.HTTP2Protocol.ALPN_PROTO_H2,
    )

    if OpenSSL._util.lib.Cryptography_HAS_ALPN:

        def test_check_alpn(self):
            c = tcp.TCPClient(("127.0.0.1", self.port))
            c.connect()
            c.convert_to_ssl(alpn_protos=[http2.HTTP2Protocol.ALPN_PROTO_H2])
            protocol = http2.HTTP2Protocol(c)
            assert protocol.check_alpn()


class TestCheckALPNMismatch(test.ServerTestBase):
    handler = EchoHandler
    ssl = dict(
        alpn_select=None,
    )

    if OpenSSL._util.lib.Cryptography_HAS_ALPN:

        def test_check_alpn(self):
            c = tcp.TCPClient(("127.0.0.1", self.port))
            c.connect()
            c.convert_to_ssl(alpn_protos=[http2.HTTP2Protocol.ALPN_PROTO_H2])
            protocol = http2.HTTP2Protocol(c)
            tutils.raises(NotImplementedError, protocol.check_alpn)


class TestPerformConnectionPreface(test.ServerTestBase):
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

    ssl = True

    def test_perform_connection_preface(self):
        c = tcp.TCPClient(("127.0.0.1", self.port))
        c.connect()
        c.convert_to_ssl()
        protocol = http2.HTTP2Protocol(c)
        protocol.perform_connection_preface()


class TestStreamIds():
    c = tcp.TCPClient(("127.0.0.1", 0))
    protocol = http2.HTTP2Protocol(c)

    def test_stream_ids(self):
        assert self.protocol.current_stream_id is None
        assert self.protocol.next_stream_id() == 1
        assert self.protocol.current_stream_id == 1
        assert self.protocol.next_stream_id() == 3
        assert self.protocol.current_stream_id == 3
        assert self.protocol.next_stream_id() == 5
        assert self.protocol.current_stream_id == 5


class TestApplySettings(test.ServerTestBase):
    class handler(tcp.BaseHandler):

        def handle(self):
            # check settings acknowledgement
            assert self.rfile.read(9) == '000000040100000000'.decode('hex')
            self.wfile.write("OK")
            self.wfile.flush()

    ssl = True

    def test_apply_settings(self):
        c = tcp.TCPClient(("127.0.0.1", self.port))
        c.connect()
        c.convert_to_ssl()
        protocol = http2.HTTP2Protocol(c)

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

        bytes = http2.HTTP2Protocol(self.c)._create_headers(
            headers, 1, end_stream=True)
        assert b''.join(bytes) ==\
            '000014010500000001824488355217caf3a69a3f87408294e7838c767f'\
            .decode('hex')

        bytes = http2.HTTP2Protocol(self.c)._create_headers(
            headers, 1, end_stream=False)
        assert b''.join(bytes) ==\
            '000014010400000001824488355217caf3a69a3f87408294e7838c767f'\
            .decode('hex')

    # TODO: add test for too large header_block_fragments


class TestCreateBody():
    c = tcp.TCPClient(("127.0.0.1", 0))
    protocol = http2.HTTP2Protocol(c)

    def test_create_body_empty(self):
        bytes = self.protocol._create_body(b'', 1)
        assert b''.join(bytes) == ''.decode('hex')

    def test_create_body_single_frame(self):
        bytes = self.protocol._create_body('foobar', 1)
        assert b''.join(bytes) == '000006000100000001666f6f626172'.decode('hex')

    def test_create_body_multiple_frames(self):
        pass
        # bytes = self.protocol._create_body('foobar' * 3000, 1)
        # TODO: add test for too large frames


class TestCreateRequest():
    c = tcp.TCPClient(("127.0.0.1", 0))

    def test_create_request_simple(self):
        bytes = http2.HTTP2Protocol(self.c).create_request('GET', '/')
        assert len(bytes) == 1
        assert bytes[0] == '000003010500000001828487'.decode('hex')

    def test_create_request_with_body(self):
        bytes = http2.HTTP2Protocol(self.c).create_request(
            'GET', '/', [(b'foo', b'bar')], 'foobar')
        assert len(bytes) == 2
        assert bytes[0] ==\
            '00000b010400000001828487408294e7838c767f'.decode('hex')
        assert bytes[1] ==\
            '000006000100000001666f6f626172'.decode('hex')


class TestReadResponse(test.ServerTestBase):
    class handler(tcp.BaseHandler):

        def handle(self):
            self.wfile.write(
                b'00000801040000000188628594e78c767f'.decode('hex'))
            self.wfile.write(
                b'000006000100000001666f6f626172'.decode('hex'))
            self.wfile.flush()

    ssl = True

    def test_read_response(self):
        c = tcp.TCPClient(("127.0.0.1", self.port))
        c.connect()
        c.convert_to_ssl()
        protocol = http2.HTTP2Protocol(c)

        status, headers, body = protocol.read_response()

        assert headers == {':status': '200', 'etag': 'foobar'}
        assert status == '200'
        assert body == b'foobar'
