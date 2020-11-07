import pytest
from io import BytesIO
from unittest import mock

from wsproto.frame_protocol import Opcode, RsvBits, Header, Frame

from mitmproxy.net.http import Headers
from mitmproxy.net import websocket_utils


@pytest.mark.parametrize("input,masking_key,payload_length", [
    (b'\x01\rserver-foobar', None, 13),
    (b'\x01\x8dasdf\x12\x16\x16\x10\x04\x01I\x00\x0e\x1c\x06\x07\x13', b'asdf', 13),
    (b'\x01~\x04\x00server-foobar', None, 1024),
    (b'\x01\x7f\x00\x00\x00\x00\x00\x02\x00\x00server-foobar', None, 131072),
])
def test_read_raw_frame(input, masking_key, payload_length):
    bio = BytesIO(input)
    bio.safe_read = bio.read

    header, frame, consumed_bytes = websocket_utils.read_raw_frame(bio)
    assert header == \
        Header(
            fin=False,
            rsv=RsvBits(rsv1=False, rsv2=False, rsv3=False),
            opcode=Opcode.TEXT,
            payload_len=payload_length,
            masking_key=masking_key,
        )
    assert frame == \
        Frame(
            opcode=Opcode.TEXT,
            payload=b'server-foobar',
            frame_finished=False,
            message_finished=False,
        )
    assert consumed_bytes == input


@mock.patch('os.urandom', return_value=b'pumpkinspumpkins')
def test_client_handshake_headers(_):
    assert websocket_utils.client_handshake_headers() == \
        Headers([
            (b'connection', b'upgrade'),
            (b'upgrade', b'websocket'),
            (b'sec-websocket-version', b'13'),
            (b'sec-websocket-key', b'cHVtcGtpbnNwdW1wa2lucw=='),
        ])
    assert websocket_utils.client_handshake_headers(b"13", b"foobar", b"foo", b"bar") == \
        Headers([
            (b'connection', b'upgrade'),
            (b'upgrade', b'websocket'),
            (b'sec-websocket-version', b'13'),
            (b'sec-websocket-key', b'foobar'),
            (b'sec-websocket-protocol', b'foo'),
            (b'sec-websocket-extensions', b'bar')
        ])


def test_server_handshake_headers():
    assert websocket_utils.server_handshake_headers("foobar", "foo", "bar") == \
        Headers([
            (b'connection', b'upgrade'),
            (b'upgrade', b'websocket'),
            (b'sec-websocket-accept', b'AzhRPA4TNwR6I/riJheN0TfR7+I='),
            (b'sec-websocket-protocol', b'foo'),
            (b'sec-websocket-extensions', b'bar'),
        ])


def test_check_handshake():
    assert not websocket_utils.check_handshake({
        "connection": "upgrade",
        "upgrade": "webFOOsocket",
        "sec-websocket-key": "foo",
    })
    assert websocket_utils.check_handshake({
        "connection": "upgrade",
        "upgrade": "websocket",
        "sec-websocket-key": "foo",
    })
    assert websocket_utils.check_handshake({
        "connection": "upgrade",
        "upgrade": "websocket",
        "sec-websocket-accept": "bar",
    })


def test_create_server_nonce():
    assert websocket_utils.create_server_nonce(b"foobar") == b"AzhRPA4TNwR6I/riJheN0TfR7+I="


def test_check_client_version():
    assert not websocket_utils.check_client_version({})
    assert not websocket_utils.check_client_version({"sec-websocket-version": b"42"})
    assert websocket_utils.check_client_version({"sec-websocket-version": b"13"})


def test_get_extensions():
    assert websocket_utils.get_extensions({}) is None
    assert websocket_utils.get_extensions({"sec-websocket-extensions": "foo"}) == "foo"


def test_get_protocol():
    assert websocket_utils.get_protocol({}) is None
    assert websocket_utils.get_protocol({"sec-websocket-protocol": "foo"}) == "foo"


def test_get_client_key():
    assert websocket_utils.get_client_key({}) is None
    assert websocket_utils.get_client_key({"sec-websocket-key": "foo"}) == "foo"


def test_get_server_accept():
    assert websocket_utils.get_server_accept({}) is None
    assert websocket_utils.get_server_accept({"sec-websocket-accept": "foo"}) == "foo"
