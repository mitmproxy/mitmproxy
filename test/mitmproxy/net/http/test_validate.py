import pytest

from mitmproxy.http import Headers
from mitmproxy.net.http.validate import (
    validate_headers,
    parse_content_length,
    parse_transfer_encoding,
)


def test_parse_content_length_ok():
    assert parse_content_length("0") == 0
    assert parse_content_length("42") == 42
    assert parse_content_length(b"0") == 0
    assert parse_content_length(b"42") == 42


@pytest.mark.parametrize(
    "cl", ["NaN", "", " ", "-1", "+1", "0x42", "010", "foo", "1, 1"]
)
def test_parse_content_length_invalid(cl):
    with pytest.raises(ValueError, match="invalid content-length"):
        parse_content_length(cl)
    with pytest.raises(ValueError, match="invalid content-length"):
        parse_content_length(cl.encode())


def test_parse_transfer_encoding_ok():
    assert parse_transfer_encoding(b"chunked") == "chunked"
    assert parse_transfer_encoding("chunked") == "chunked"
    assert parse_transfer_encoding("gzip,chunked") == "gzip,chunked"
    assert parse_transfer_encoding("gzip, chunked") == "gzip,chunked"


@pytest.mark.parametrize(
    "te",
    [
        "unknown",
        "chunked,chunked",
        "chunked,gzip",
        "",
        "chunKed",
    ],
)
def test_parse_transfer_encoding_invalid(te):
    with pytest.raises(ValueError, match="transfer-encoding"):
        parse_transfer_encoding(te)
    with pytest.raises(ValueError, match="transfer-encoding"):
        parse_transfer_encoding(te.encode())


def test_validate_headers_ok():
    validate_headers(
        Headers(content_length="42"),
    )


@pytest.mark.parametrize(
    "headers",
    [
        pytest.param(
            Headers(transfer_encoding="chunked", content_length="42"), id="cl.te"
        ),
        pytest.param(Headers([(b"content-length ", b"42")]), id="whitespace"),
        pytest.param(Headers(content_length="-42"), id="invalid-cl"),
        pytest.param(Headers(transfer_encoding="unknown"), id="invalid-te"),
        pytest.param(
            Headers([(b"content-length", b"42"), (b"content-length", b"43")]),
            id="multi-cl",
        ),
        pytest.param(
            Headers([(b"transfer-encoding", b""), (b"transfer-encoding", b"chunked")]),
            id="multi-te",
        ),
    ],
)
def test_validate_headers_invalid(headers: Headers):
    # both content-length and chunked (possible request smuggling)
    with pytest.raises(ValueError):
        validate_headers(headers)
