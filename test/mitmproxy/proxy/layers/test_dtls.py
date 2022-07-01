import pytest

from mitmproxy.proxy.layers import dtls
from mitmproxy.utils import data


tlsdata = data.Data(__name__)


def test_is_tls_handshake_record():
    assert dtls.is_dtls_handshake_record(bytes.fromhex("16fefd"))
    assert not dtls.is_dtls_handshake_record(bytes.fromhex("160300"))
    assert not dtls.is_dtls_handshake_record(bytes.fromhex("16fefe"))
    assert not dtls.is_dtls_handshake_record(bytes.fromhex(""))
    assert not dtls.is_dtls_handshake_record(bytes.fromhex("160304"))
    assert not dtls.is_dtls_handshake_record(bytes.fromhex("150301"))


def test_record_contents():
    data = bytes.fromhex("16fefd00000000000000000002beef" "16fefd00000000000000000001ff")
    assert list(dtls.dtls_handshake_record_contents(data)) == [b"\xbe\xef", b"\xff"]
    for i in range(12):
        assert list(dtls.dtls_handshake_record_contents(data[:i])) == []


def test_record_contents_err():
    with pytest.raises(ValueError, match="Expected DTLS record"):
        next(dtls.dtls_handshake_record_contents(b"GET /this-will-cause-error"))

    empty_record = bytes.fromhex("16fefd00000000000000000000")
    with pytest.raises(ValueError, match="Record must not be empty"):
        next(dtls.dtls_handshake_record_contents(empty_record))


client_hello_no_extensions = bytes.fromhex(
    "010000360000000000000036fefd62be32f048777da890ddd213b0cb8dc3e2903f88dda1cd5f67808e1169110e840000000"
    "cc02bc02fc00ac014c02cc03001000000"
)
client_hello_with_extensions = bytes.fromhex(
    "16fefd00000000000000000085"    # record layer
    "010000790000000000000079"      # hanshake layer
    "fefd62bf0e0bf809df43e7669197be831919878b1a72c07a584d3c0a8ca6665878010000000cc02bc02fc00ac014c02cc0"
    "3001000043000d0010000e0403050306030401050106010807ff01000100000a00080006001d00170018000b00020100001"
    "7000000000010000e00000b6578616d706c652e636f6d"
)


def test_get_client_hello():
    single_record = bytes.fromhex("16fefd00000000000000000042") + client_hello_no_extensions
    assert dtls.get_dtls_client_hello(single_record) == client_hello_no_extensions

    split_over_two_records = (
        bytes.fromhex("16fefd00000000000000000020")
        + client_hello_no_extensions[:32]
        + bytes.fromhex("16fefd00000000000000000022")
        + client_hello_no_extensions[32:]
    )
    assert dtls.get_dtls_client_hello(split_over_two_records) == client_hello_no_extensions

    incomplete = split_over_two_records[:42]
    assert dtls.get_dtls_client_hello(incomplete) is None


def test_parse_client_hello():
    assert dtls.parse_client_hello(client_hello_with_extensions).sni == "example.com"
    assert dtls.parse_client_hello(client_hello_with_extensions[:50]) is None
    with pytest.raises(ValueError):
        dtls.parse_client_hello(
            # Server Name Length longer than actual Server Name
            client_hello_with_extensions[:-16] + b"\x00\x0e\x00\x00\x20\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
        )
