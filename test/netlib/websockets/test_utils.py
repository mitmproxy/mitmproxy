import pytest

from netlib import http
from netlib import websockets


class TestUtils(object):

    def test_client_handshake_headers(self):
        h = websockets.client_handshake_headers(version='42')
        assert h['sec-websocket-version'] == '42'

        h = websockets.client_handshake_headers(key='some-key')
        assert h['sec-websocket-key'] == 'some-key'

        h = websockets.client_handshake_headers(protocol='foobar')
        assert h['sec-websocket-protocol'] == 'foobar'

        h = websockets.client_handshake_headers(extensions='foo; bar')
        assert h['sec-websocket-extensions'] == 'foo; bar'

    def test_server_handshake_headers(self):
        h = websockets.server_handshake_headers('some-key')
        assert h['sec-websocket-accept'] == '8iILEZtcVdtFD7MDlPKip9ec9nw='
        assert 'sec-websocket-protocol' not in h
        assert 'sec-websocket-extensions' not in h

        h = websockets.server_handshake_headers('some-key', 'foobar', 'foo; bar')
        assert h['sec-websocket-accept'] == '8iILEZtcVdtFD7MDlPKip9ec9nw='
        assert h['sec-websocket-protocol'] == 'foobar'
        assert h['sec-websocket-extensions'] == 'foo; bar'

    @pytest.mark.parametrize("input,expected", [
        ([(b'connection', b'upgrade'), (b'upgrade', b'websocket'), (b'sec-websocket-key', b'foobar')], True),
        ([(b'connection', b'upgrade'), (b'upgrade', b'websocket'), (b'sec-websocket-accept', b'foobar')], True),
        ([(b'Connection', b'UpgRaDe'), (b'Upgrade', b'WebSocKeT'), (b'Sec-WebSockeT-KeY', b'foobar')], True),
        ([(b'Connection', b'UpgRaDe'), (b'Upgrade', b'WebSocKeT'), (b'Sec-WebSockeT-AccePt', b'foobar')], True),
        ([(b'connection', b'foo'), (b'upgrade', b'bar'), (b'sec-websocket-key', b'foobar')], False),
        ([(b'connection', b'upgrade'), (b'upgrade', b'websocket')], False),
        ([(b'connection', b'upgrade'), (b'sec-websocket-key', b'foobar')], False),
        ([(b'upgrade', b'websocket'), (b'sec-websocket-key', b'foobar')], False),
        ([], False),
    ])
    def test_check_handshake(self, input, expected):
        h = http.Headers(input)
        assert websockets.check_handshake(h) == expected

    @pytest.mark.parametrize("input,expected", [
        ([(b'sec-websocket-version', b'13')], True),
        ([(b'Sec-WebSockeT-VerSion', b'13')], True),
        ([(b'sec-websocket-version', b'9')], False),
        ([(b'sec-websocket-version', b'42')], False),
        ([(b'sec-websocket-version', b'')], False),
        ([], False),
    ])
    def test_check_client_version(self, input, expected):
        h = http.Headers(input)
        assert websockets.check_client_version(h) == expected

    @pytest.mark.parametrize("input,expected", [
        ('foobar', b'AzhRPA4TNwR6I/riJheN0TfR7+I='),
        (b'foobar', b'AzhRPA4TNwR6I/riJheN0TfR7+I='),
    ])
    def test_create_server_nonce(self, input, expected):
        assert websockets.create_server_nonce(input) == expected

    @pytest.mark.parametrize("input,expected", [
        ([(b'sec-websocket-extensions', b'foo; bar')], 'foo; bar'),
        ([(b'Sec-WebSockeT-ExteNsionS', b'foo; bar')], 'foo; bar'),
        ([(b'sec-websocket-extensions', b'')], ''),
        ([], None),
    ])
    def test_get_extensions(self, input, expected):
        h = http.Headers(input)
        assert websockets.get_extensions(h) == expected

    @pytest.mark.parametrize("input,expected", [
        ([(b'sec-websocket-protocol', b'foobar')], 'foobar'),
        ([(b'Sec-WebSockeT-ProTocoL', b'foobar')], 'foobar'),
        ([(b'sec-websocket-protocol', b'')], ''),
        ([], None),
    ])
    def test_get_protocol(self, input, expected):
        h = http.Headers(input)
        assert websockets.get_protocol(h) == expected

    @pytest.mark.parametrize("input,expected", [
        ([(b'sec-websocket-key', b'foobar')], 'foobar'),
        ([(b'Sec-WebSockeT-KeY', b'foobar')], 'foobar'),
        ([(b'sec-websocket-key', b'')], ''),
        ([], None),
    ])
    def test_get_client_key(self, input, expected):
        h = http.Headers(input)
        assert websockets.get_client_key(h) == expected

    @pytest.mark.parametrize("input,expected", [
        ([(b'sec-websocket-accept', b'foobar')], 'foobar'),
        ([(b'Sec-WebSockeT-AccepT', b'foobar')], 'foobar'),
        ([(b'sec-websocket-accept', b'')], ''),
        ([], None),
    ])
    def test_get_server_accept(self, input, expected):
        h = http.Headers(input)
        assert websockets.get_server_accept(h) == expected
