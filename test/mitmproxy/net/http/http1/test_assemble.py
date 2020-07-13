import pytest

from mitmproxy import exceptions
from mitmproxy.net.http import Headers
from mitmproxy.net.http.http1.assemble import (
    assemble_request, assemble_request_head, assemble_response,
    assemble_response_head, _assemble_request_line, _assemble_request_headers,
    _assemble_response_headers,
    assemble_body)
from mitmproxy.test.tutils import treq, tresp


def test_assemble_request():
    assert assemble_request(treq()) == (
        b"GET /path HTTP/1.1\r\n"
        b"header: qvalue\r\n"
        b"content-length: 7\r\n"
        b"\r\n"
        b"content"
    )

    with pytest.raises(exceptions.HttpException):
        assemble_request(treq(content=None))


def test_assemble_request_head():
    c = assemble_request_head(treq(content=b"foo"))
    assert b"GET" in c
    assert b"qvalue" in c
    assert b"content-length" in c
    assert b"foo" not in c


def test_assemble_response():
    assert assemble_response(tresp()) == (
        b"HTTP/1.1 200 OK\r\n"
        b"header-response: svalue\r\n"
        b"content-length: 7\r\n"
        b"\r\n"
        b"message"
    )

    with pytest.raises(exceptions.HttpException):
        assemble_response(tresp(content=None))


def test_assemble_response_head():
    c = assemble_response_head(tresp())
    assert b"200" in c
    assert b"svalue" in c
    assert b"message" not in c


def test_assemble_body():
    c = list(assemble_body(Headers(), [b"body"]))
    assert c == [b"body"]

    c = list(assemble_body(Headers(transfer_encoding="chunked"), [b"123456789a", b""]))
    assert c == [b"a\r\n123456789a\r\n", b"0\r\n\r\n"]

    c = list(assemble_body(Headers(transfer_encoding="chunked"), [b"123456789a"]))
    assert c == [b"a\r\n123456789a\r\n", b"0\r\n\r\n"]


def test_assemble_request_line():
    assert _assemble_request_line(treq().data) == b"GET /path HTTP/1.1"

    authority_request = treq(method=b"CONNECT", first_line_format="authority").data
    assert _assemble_request_line(authority_request) == b"CONNECT address:22 HTTP/1.1"

    absolute_request = treq(first_line_format="absolute").data
    assert _assemble_request_line(absolute_request) == b"GET http://address:22/path HTTP/1.1"

    with pytest.raises(RuntimeError):
        _assemble_request_line(treq(first_line_format="invalid_form").data)


def test_assemble_request_headers():
    # https://github.com/mitmproxy/mitmproxy/issues/186
    r = treq(content=b"")
    r.headers["Transfer-Encoding"] = "chunked"
    c = _assemble_request_headers(r.data)
    assert b"Transfer-Encoding" in c


def test_assemble_response_headers():
    # https://github.com/mitmproxy/mitmproxy/issues/186
    r = tresp(content=b"")
    r.headers["Transfer-Encoding"] = "chunked"
    c = _assemble_response_headers(r)
    assert b"Transfer-Encoding" in c
