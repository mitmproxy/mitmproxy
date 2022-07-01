from mitmproxy import tls


CLIENT_HELLO_NO_EXTENSIONS = bytes.fromhex(
    # No Record or Handshake layer header
    "fefd62bf5560a83b2525186d38fb6459837656d7f11"
    "fb630cd44683bb9d9681204c50000000c00020003000a00050004000901000000"
)
FULL_CLIENT_HELLO_NO_EXTENSIONS = (
    b"\x16\xfe\xfd\x00\x00\x00\x00\x00\x00\x00\x00\x00\x42"  # record layer
    b"\x01\x00\x00\x34\x00\x00\x00\x00\x00\x00\x00\x36" + CLIENT_HELLO_NO_EXTENSIONS  # handshake header
)


class TestDTLSClientHello:
    def test_no_extensions(self):
        c = tls.ClientHello(CLIENT_HELLO_NO_EXTENSIONS, dtls=True)
        assert repr(c)
        assert c.sni is None
        assert c.cipher_suites == [2, 3, 10, 5, 4, 9]
        assert c.alpn_protocols == []
        assert c.extensions == []

    def test_extensions(self):
        # No Record or Handshake layer header
        data = bytes.fromhex(
            "fefd62bf60ba96532f63c4e53196174ff5016d949420d7f970a6b08a9e2a5a8209af0000"
            "000c00020003000a000500040009"
            "01000055000d0010000e0403050306030401050106010807ff01000100000a00080006001d"
            "00170018000b000201000017000000000010000e00000b6578616d706c652e636f6d0010000e"
            "000c02683208687474702f312e31"
        )
        c = tls.ClientHello(data, dtls=True)
        assert repr(c)
        assert c.sni == "example.com"
        assert c.cipher_suites == [2, 3, 10, 5, 4, 9]
        assert c.alpn_protocols == [b"h2", b"http/1.1"]
        assert c.extensions == [
            (13, b'\x00\x0e\x04\x03\x05\x03\x06\x03\x04\x01\x05\x01\x06\x01\x08\x07'),
            (65281, b'\x00'),
            (10, b'\x00\x06\x00\x1d\x00\x17\x00\x18'),
            (11, b'\x01\x00'), (23, b''),
            (0, b'\x00\x0e\x00\x00\x0bexample.com'),
            (16, b'\x00\x0c\x02h2\x08http/1.1')
        ]
