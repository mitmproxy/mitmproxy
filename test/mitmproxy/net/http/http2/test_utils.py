import pytest

from mitmproxy.net.http.http2 import parse_headers


class TestHttp2ParseHeaders:

    def test_relative(self):
        h = dict([
            (':authority', "127.0.0.1:1234"),
            (':method', 'GET'),
            (':scheme', 'https'),
            (':path', '/'),
        ])
        first_line_format, method, scheme, host, port, path = parse_headers(h)
        assert first_line_format == 'relative'
        assert method == b'GET'
        assert scheme == b'https'
        assert host == b'127.0.0.1'
        assert port == 1234
        assert path == b'/'

    def test_absolute(self):
        h = dict([
            (':authority', "127.0.0.1:1234"),
            (':method', 'GET'),
            (':scheme', 'https'),
            (':path', 'https://127.0.0.1:4321'),
        ])
        first_line_format, method, scheme, host, port, path = parse_headers(h)
        assert first_line_format == 'absolute'
        assert method == b'GET'
        assert scheme == b'https'
        assert host == b'127.0.0.1'
        assert port == 1234
        assert path == b'https://127.0.0.1:4321'

    @pytest.mark.parametrize("scheme, expected_port", [
        ('http', 80),
        ('https', 443),
    ])
    def test_without_port(self, scheme, expected_port):
        h = dict([
            (':authority', "127.0.0.1"),
            (':method', 'GET'),
            (':scheme', scheme),
            (':path', '/'),
        ])
        _, _, _, _, port, _ = parse_headers(h)
        assert port == expected_port

    def test_without_authority(self):
        h = dict([
            (':method', 'GET'),
            (':scheme', 'https'),
            (':path', '/'),
        ])
        _, _, _, host, _, _ = parse_headers(h)
        assert host == b'localhost'

    def test_connect(self):
        h = dict([
            (':authority', "127.0.0.1"),
            (':method', 'CONNECT'),
            (':scheme', 'https'),
            (':path', '/'),
        ])

        with pytest.raises(NotImplementedError):
            parse_headers(h)
