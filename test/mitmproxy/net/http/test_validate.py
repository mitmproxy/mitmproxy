import pytest

from mitmproxy.http import Headers
from mitmproxy.http import Response
from mitmproxy.net.http.validate import parse_content_length
from mitmproxy.net.http.validate import parse_transfer_encoding
from mitmproxy.net.http.validate import validate_headers


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
        "chun ked",
    ],
)
def test_parse_transfer_encoding_invalid(te):
    with pytest.raises(ValueError, match="transfer-encoding"):
        parse_transfer_encoding(te)
    with pytest.raises(ValueError, match="transfer-encoding"):
        parse_transfer_encoding(te.encode())


def test_validate_headers_ok():
    validate_headers(
        Response.make(headers=Headers(content_length="42")),
    )


@pytest.mark.parametrize(
    "headers",
    [
        pytest.param(
            Headers(transfer_encoding="chunked", content_length="42"), id="cl.te"
        ),
        pytest.param(Headers([(b"content-length ", b"42")]), id="whitespace-key"),
        pytest.param(Headers([(b"content-length", b"42 ")]), id="whitespace-value"),
        pytest.param(Headers(content_length="-42"), id="negative-cl"),
        pytest.param(Headers(content_length="042"), id="zero-prefixed-cl"),
        pytest.param(Headers(transfer_encoding="unknown"), id="unknown-te"),
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
    resp = Response.make()
    resp.headers = (
        headers  # update manually as Response.make() fixes content-length headers.
    )
    with pytest.raises(ValueError):
        validate_headers(resp)


def test_validate_headers_te_forbidden():
    te_headers = Headers(transfer_encoding="chunked")
    resp = Response.make(headers=te_headers)
    resp.headers = te_headers
    resp.http_version = "HTTP/1.0"

    with pytest.raises(ValueError):
        validate_headers(resp)

    resp = Response.make(status_code=204)
    resp.headers = te_headers
    with pytest.raises(ValueError):
        validate_headers(Response.make(headers=te_headers, status_code=204))
