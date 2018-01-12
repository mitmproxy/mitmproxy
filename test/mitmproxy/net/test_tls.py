import io

import pytest

from mitmproxy import exceptions
from mitmproxy.net import tls
from mitmproxy.net.tcp import TCPClient
from test.mitmproxy.net.test_tcp import EchoHandler
from . import tservers

CLIENT_HELLO_NO_EXTENSIONS = bytes.fromhex(
    "03015658a756ab2c2bff55f636814deac086b7ca56b65058c7893ffc6074f5245f70205658a75475103a152637"
    "78e1bb6d22e8bbd5b6b0a3a59760ad354e91ba20d353001a0035002f000a000500040009000300060008006000"
    "61006200640100"
)
FULL_CLIENT_HELLO_NO_EXTENSIONS = (
    b"\x16\x03\x03\x00\x65"  # record layer
    b"\x01\x00\x00\x61" +  # handshake header
    CLIENT_HELLO_NO_EXTENSIONS
)


class TestMasterSecretLogger(tservers.ServerTestBase):
    handler = EchoHandler
    ssl = dict(
        cipher_list="AES256-SHA"
    )

    def test_log(self, tmpdir):
        testval = b"echo!\n"
        _logfun = tls.log_master_secret

        logfile = str(tmpdir.join("foo", "bar", "logfile"))
        tls.log_master_secret = tls.MasterSecretLogger(logfile)

        c = TCPClient(("127.0.0.1", self.port))
        with c.connect():
            c.convert_to_tls()
            c.wfile.write(testval)
            c.wfile.flush()
            assert c.rfile.readline() == testval
            c.finish()

            tls.log_master_secret.close()
            with open(logfile, "rb") as f:
                assert f.read().count(b"CLIENT_RANDOM") == 2

        tls.log_master_secret = _logfun

    def test_create_logfun(self):
        assert isinstance(
            tls.MasterSecretLogger.create_logfun("test"),
            tls.MasterSecretLogger)
        assert not tls.MasterSecretLogger.create_logfun(False)


class TestTLSInvalid:
    def test_invalid_ssl_method_should_fail(self):
        fake_ssl_method = 100500
        with pytest.raises(exceptions.TlsException):
            tls.create_client_context(method=fake_ssl_method)

    def test_alpn_error(self):
        with pytest.raises(exceptions.TlsException, match="must be a function"):
            tls.create_client_context(alpn_select_callback="foo")

        with pytest.raises(exceptions.TlsException, match="ALPN error"):
            tls.create_client_context(alpn_select="foo", alpn_select_callback="bar")


def test_is_record_magic():
    assert not tls.is_tls_record_magic(b"POST /")
    assert not tls.is_tls_record_magic(b"\x16\x03")
    assert not tls.is_tls_record_magic(b"\x16\x03\x04")
    assert tls.is_tls_record_magic(b"\x16\x03\x00")
    assert tls.is_tls_record_magic(b"\x16\x03\x01")
    assert tls.is_tls_record_magic(b"\x16\x03\x02")
    assert tls.is_tls_record_magic(b"\x16\x03\x03")


def test_get_client_hello():
    rfile = io.BufferedReader(io.BytesIO(
        FULL_CLIENT_HELLO_NO_EXTENSIONS
    ))
    assert tls.get_client_hello(rfile)

    rfile = io.BufferedReader(io.BytesIO(
        FULL_CLIENT_HELLO_NO_EXTENSIONS[:30]
    ))
    with pytest.raises(exceptions.TlsProtocolException, message="Unexpected EOF"):
        tls.get_client_hello(rfile)

    rfile = io.BufferedReader(io.BytesIO(
        b"GET /"
    ))
    with pytest.raises(exceptions.TlsProtocolException, message="Expected TLS record"):
        tls.get_client_hello(rfile)


class TestClientHello:
    def test_no_extensions(self):
        c = tls.ClientHello(CLIENT_HELLO_NO_EXTENSIONS)
        assert repr(c)
        assert c.sni is None
        assert c.cipher_suites == [53, 47, 10, 5, 4, 9, 3, 6, 8, 96, 97, 98, 100]
        assert c.alpn_protocols == []
        assert c.extensions == []

    def test_extensions(self):
        data = bytes.fromhex(
            "03033b70638d2523e1cba15f8364868295305e9c52aceabda4b5147210abc783e6e1000022c02bc02fc02cc030"
            "cca9cca8cc14cc13c009c013c00ac014009c009d002f0035000a0100006cff0100010000000010000e00000b65"
            "78616d706c652e636f6d0017000000230000000d00120010060106030501050304010403020102030005000501"
            "00000000001200000010000e000c02683208687474702f312e3175500000000b00020100000a00080006001d00"
            "170018"
        )
        c = tls.ClientHello(data)
        assert repr(c)
        assert c.sni == 'example.com'
        assert c.cipher_suites == [
            49195, 49199, 49196, 49200, 52393, 52392, 52244, 52243, 49161,
            49171, 49162, 49172, 156, 157, 47, 53, 10
        ]
        assert c.alpn_protocols == [b'h2', b'http/1.1']
        assert c.extensions == [
            (65281, b'\x00'),
            (0, b'\x00\x0e\x00\x00\x0bexample.com'),
            (23, b''),
            (35, b''),
            (13, b'\x00\x10\x06\x01\x06\x03\x05\x01\x05\x03\x04\x01\x04\x03\x02\x01\x02\x03'),
            (5, b'\x01\x00\x00\x00\x00'),
            (18, b''),
            (16, b'\x00\x0c\x02h2\x08http/1.1'),
            (30032, b''),
            (11, b'\x01\x00'),
            (10, b'\x00\x06\x00\x1d\x00\x17\x00\x18')
        ]

    def test_from_file(self):
        rfile = io.BufferedReader(io.BytesIO(
            FULL_CLIENT_HELLO_NO_EXTENSIONS
        ))
        assert tls.ClientHello.from_file(rfile)

        rfile = io.BufferedReader(io.BytesIO(
            b""
        ))
        with pytest.raises(exceptions.TlsProtocolException):
            tls.ClientHello.from_file(rfile)

        rfile = io.BufferedReader(io.BytesIO(
            b"\x16\x03\x03\x00\x07"  # record layer
            b"\x01\x00\x00\x03" +  # handshake header
            b"foo"
        ))
        with pytest.raises(exceptions.TlsProtocolException, message='Cannot parse Client Hello'):
            tls.ClientHello.from_file(rfile)
