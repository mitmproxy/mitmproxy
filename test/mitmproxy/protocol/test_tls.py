from mitmproxy.proxy.protocol.tls import TlsClientHello


class TestClientHello:

    def test_no_extensions(self):
        data = bytes.fromhex(
            "03015658a756ab2c2bff55f636814deac086b7ca56b65058c7893ffc6074f5245f70205658a75475103a152637"
            "78e1bb6d22e8bbd5b6b0a3a59760ad354e91ba20d353001a0035002f000a000500040009000300060008006000"
            "61006200640100"
        )
        c = TlsClientHello(data)
        assert c.sni is None
        assert c.alpn_protocols == []

    def test_extensions(self):
        data = bytes.fromhex(
            "03033b70638d2523e1cba15f8364868295305e9c52aceabda4b5147210abc783e6e1000022c02bc02fc02cc030"
            "cca9cca8cc14cc13c009c013c00ac014009c009d002f0035000a0100006cff0100010000000010000e00000b65"
            "78616d706c652e636f6d0017000000230000000d00120010060106030501050304010403020102030005000501"
            "00000000001200000010000e000c02683208687474702f312e3175500000000b00020100000a00080006001d00"
            "170018"
        )
        c = TlsClientHello(data)
        assert c.sni == 'example.com'
        assert c.alpn_protocols == [b'h2', b'http/1.1']
