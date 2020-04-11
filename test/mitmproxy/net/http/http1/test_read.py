from io import BytesIO
from unittest.mock import Mock
import pytest

from mitmproxy import exceptions
from mitmproxy.net.http import Headers
from mitmproxy.net.http.http1.read import (
    read_request, read_response, read_request_head,
    read_response_head, read_body, connection_close, expected_http_body_size, _get_first_line,
    _read_request_line, _parse_authority_form, _read_response_line, _check_http_version,
    _read_headers, _read_chunked, get_header_tokens
)
from mitmproxy.test.tutils import treq, tresp


def test_get_header_tokens():
    headers = Headers()
    assert get_header_tokens(headers, "foo") == []
    headers["foo"] = "bar"
    assert get_header_tokens(headers, "foo") == ["bar"]
    headers["foo"] = "bar, voing"
    assert get_header_tokens(headers, "foo") == ["bar", "voing"]
    headers.set_all("foo", ["bar, voing", "oink"])
    assert get_header_tokens(headers, "foo") == ["bar", "voing", "oink"]


@pytest.mark.parametrize("input", [
    b"GET / HTTP/1.1\r\n\r\nskip",
    b"GET  / HTTP/1.1\r\n\r\nskip",
    b"GET  /  HTTP/1.1\r\n\r\nskip",
    b"GET   /   HTTP/1.1   \r\n\r\nskip",
])
def test_read_request(input):
    rfile = BytesIO(input)
    r = read_request(rfile)
    assert r.method == "GET"
    assert r.content == b""
    assert r.http_version == "HTTP/1.1"
    assert r.timestamp_end
    assert rfile.read() == b"skip"


@pytest.mark.parametrize("input", [
    b"CONNECT :0 0",
])
def test_read_request_error(input):
    rfile = BytesIO(input)
    with pytest.raises(exceptions.HttpException):
        read_request(rfile)


def test_read_request_head():
    rfile = BytesIO(
        b"GET / HTTP/1.1\r\n"
        b"Content-Length: 4\r\n"
        b"\r\n"
        b"skip"
    )
    rfile.reset_timestamps = Mock()
    rfile.first_byte_timestamp = 42
    r = read_request_head(rfile)
    assert r.method == "GET"
    assert r.headers["Content-Length"] == "4"
    assert r.content is None
    assert rfile.reset_timestamps.called
    assert r.timestamp_start == 42
    assert rfile.read() == b"skip"


@pytest.mark.parametrize("input", [
    b"HTTP/1.1 418 I'm a teapot\r\n\r\nbody",
    b"HTTP/1.1   418 I'm a teapot\r\n\r\nbody",
    b"HTTP/1.1   418   I'm a teapot\r\n\r\nbody",
    b"HTTP/1.1   418   I'm a teapot   \r\n\r\nbody",
])
def test_read_response(input):
    req = treq()
    rfile = BytesIO(input)
    r = read_response(rfile, req)
    assert r.http_version == "HTTP/1.1"
    assert r.status_code == 418
    assert r.reason == "I'm a teapot"
    assert r.content == b"body"
    assert r.timestamp_end


def test_read_response_head():
    rfile = BytesIO(
        b"HTTP/1.1 418 I'm a teapot\r\n"
        b"Content-Length: 4\r\n"
        b"\r\n"
        b"skip"
    )
    rfile.reset_timestamps = Mock()
    rfile.first_byte_timestamp = 42
    r = read_response_head(rfile)
    assert r.status_code == 418
    assert r.headers["Content-Length"] == "4"
    assert r.content is None
    assert rfile.reset_timestamps.called
    assert r.timestamp_start == 42
    assert rfile.read() == b"skip"


class TestReadBody:
    def test_chunked(self):
        rfile = BytesIO(b"3\r\nfoo\r\n0\r\n\r\nbar")
        body = b"".join(read_body(rfile, None))
        assert body == b"foo"
        assert rfile.read() == b"bar"

    def test_known_size(self):
        rfile = BytesIO(b"foobar")
        body = b"".join(read_body(rfile, 3))
        assert body == b"foo"
        assert rfile.read() == b"bar"

    def test_known_size_limit(self):
        rfile = BytesIO(b"foobar")
        with pytest.raises(exceptions.HttpException):
            b"".join(read_body(rfile, 3, 2))

    def test_known_size_too_short(self):
        rfile = BytesIO(b"foo")
        with pytest.raises(exceptions.HttpException):
            b"".join(read_body(rfile, 6))

    def test_unknown_size(self):
        rfile = BytesIO(b"foobar")
        body = b"".join(read_body(rfile, -1))
        assert body == b"foobar"

    def test_unknown_size_limit(self):
        rfile = BytesIO(b"foobar")
        with pytest.raises(exceptions.HttpException):
            b"".join(read_body(rfile, -1, 3))

    def test_max_chunk_size(self):
        rfile = BytesIO(b"123456")
        assert list(read_body(rfile, -1, max_chunk_size=None)) == [b"123456"]
        rfile = BytesIO(b"123456")
        assert list(read_body(rfile, -1, max_chunk_size=1)) == [b"1", b"2", b"3", b"4", b"5", b"6"]


def test_connection_close():
    headers = Headers()
    assert connection_close(b"HTTP/1.0", headers)
    assert not connection_close(b"HTTP/1.1", headers)

    headers["connection"] = "keep-alive"
    assert not connection_close(b"HTTP/1.1", headers)

    headers["connection"] = "close"
    assert connection_close(b"HTTP/1.1", headers)

    headers["connection"] = "foobar"
    assert connection_close(b"HTTP/1.0", headers)
    assert not connection_close(b"HTTP/1.1", headers)


def test_expected_http_body_size():
    # Expect: 100-continue
    assert expected_http_body_size(
        treq(headers=Headers(expect="100-continue", content_length="42")),
        expect_continue_as_0=True
    ) == 0
    # Expect: 100-continue
    assert expected_http_body_size(
        treq(headers=Headers(expect="100-continue", content_length="42")),
        expect_continue_as_0=False
    ) == 42

    # http://tools.ietf.org/html/rfc7230#section-3.3
    assert expected_http_body_size(
        treq(method=b"HEAD"),
        tresp(headers=Headers(content_length="42"))
    ) == 0
    assert expected_http_body_size(
        treq(method=b"CONNECT"),
        tresp()
    ) == 0
    for code in (100, 204, 304):
        assert expected_http_body_size(
            treq(),
            tresp(status_code=code)
        ) == 0

    # chunked
    assert expected_http_body_size(
        treq(headers=Headers(transfer_encoding="chunked")),
    ) is None

    # explicit length
    for val in (b"foo", b"-7"):
        with pytest.raises(exceptions.HttpSyntaxException):
            expected_http_body_size(
                treq(headers=Headers(content_length=val))
            )
    assert expected_http_body_size(
        treq(headers=Headers(content_length="42"))
    ) == 42

    # more than 1 content-length headers with same value
    assert expected_http_body_size(
        treq(headers=Headers([(b'content-length', b'42'), (b'content-length', b'42')]))
    ) == 42

    # more than 1 content-length headers with conflicting value
    with pytest.raises(exceptions.HttpSyntaxException):
        expected_http_body_size(
            treq(headers=Headers([(b'content-length', b'42'), (b'content-length', b'45')]))
        )

    # no length
    assert expected_http_body_size(
        treq(headers=Headers())
    ) == 0
    assert expected_http_body_size(
        treq(headers=Headers()), tresp(headers=Headers())
    ) == -1


def test_get_first_line():
    rfile = BytesIO(b"foo\r\nbar")
    assert _get_first_line(rfile) == b"foo"

    rfile = BytesIO(b"\r\nfoo\r\nbar")
    assert _get_first_line(rfile) == b"foo"

    with pytest.raises(exceptions.HttpReadDisconnect):
        rfile = BytesIO(b"")
        _get_first_line(rfile)

    with pytest.raises(exceptions.HttpReadDisconnect):
        rfile = Mock()
        rfile.readline.side_effect = exceptions.TcpDisconnect
        _get_first_line(rfile)


def test_read_request_line():
    def t(b):
        return _read_request_line(BytesIO(b))

    assert (t(b"GET / HTTP/1.1") ==
            ("relative", b"GET", None, None, None, b"/", b"HTTP/1.1"))
    assert (t(b"OPTIONS * HTTP/1.1") ==
            ("relative", b"OPTIONS", None, None, None, b"*", b"HTTP/1.1"))
    assert (t(b"CONNECT foo:42 HTTP/1.1") ==
            ("authority", b"CONNECT", None, b"foo", 42, None, b"HTTP/1.1"))
    assert (t(b"GET http://foo:42/bar HTTP/1.1") ==
            ("absolute", b"GET", b"http", b"foo", 42, b"/bar", b"HTTP/1.1"))

    with pytest.raises(exceptions.HttpSyntaxException):
        t(b"GET / WTF/1.1")
    with pytest.raises(exceptions.HttpSyntaxException):
        t(b"this is not http")
    with pytest.raises(exceptions.HttpReadDisconnect):
        t(b"")


def test_parse_authority_form():
    assert _parse_authority_form(b"foo:42") == (b"foo", 42)
    assert _parse_authority_form(b"[2001:db8:42::]:443") == (b"2001:db8:42::", 443)
    with pytest.raises(exceptions.HttpSyntaxException):
        _parse_authority_form(b"foo")
    with pytest.raises(exceptions.HttpSyntaxException):
        _parse_authority_form(b"foo:bar")
    with pytest.raises(exceptions.HttpSyntaxException):
        _parse_authority_form(b"foo:99999999")
    with pytest.raises(exceptions.HttpSyntaxException):
        _parse_authority_form(b"f\x00oo:80")


def test_read_response_line():
    def t(b):
        return _read_response_line(BytesIO(b))

    assert t(b"HTTP/1.1 200 OK") == (b"HTTP/1.1", 200, b"OK")
    assert t(b"HTTP/1.1 200") == (b"HTTP/1.1", 200, b"")

    # https://github.com/mitmproxy/mitmproxy/issues/784
    assert t(b"HTTP/1.1 200 Non-Autoris\xc3\xa9") == (b"HTTP/1.1", 200, b"Non-Autoris\xc3\xa9")

    with pytest.raises(exceptions.HttpSyntaxException):
        assert t(b"HTTP/1.1")

    with pytest.raises(exceptions.HttpSyntaxException):
        t(b"HTTP/1.1 OK OK")
    with pytest.raises(exceptions.HttpSyntaxException):
        t(b"WTF/1.1 200 OK")
    with pytest.raises(exceptions.HttpReadDisconnect):
        t(b"")


def test_check_http_version():
    _check_http_version(b"HTTP/0.9")
    _check_http_version(b"HTTP/1.0")
    _check_http_version(b"HTTP/1.1")
    _check_http_version(b"HTTP/2.0")
    with pytest.raises(exceptions.HttpSyntaxException):
        _check_http_version(b"WTF/1.0")
    with pytest.raises(exceptions.HttpSyntaxException):
        _check_http_version(b"HTTP/1.10")
    with pytest.raises(exceptions.HttpSyntaxException):
        _check_http_version(b"HTTP/1.b")


class TestReadHeaders:
    @staticmethod
    def _read(data):
        return _read_headers(BytesIO(data))

    def test_read_simple(self):
        data = (
            b"Header: one\r\n"
            b"Header2: two\r\n"
            b"\r\n"
        )
        headers = self._read(data)
        assert headers.fields == ((b"Header", b"one"), (b"Header2", b"two"))

    def test_read_multi(self):
        data = (
            b"Header: one\r\n"
            b"Header: two\r\n"
            b"\r\n"
        )
        headers = self._read(data)
        assert headers.fields == ((b"Header", b"one"), (b"Header", b"two"))

    def test_read_continued(self):
        data = (
            b"Header: one\r\n"
            b"\ttwo\r\n"
            b"Header2: three\r\n"
            b"\r\n"
        )
        headers = self._read(data)
        assert headers.fields == ((b"Header", b"one\r\n two"), (b"Header2", b"three"))

    def test_read_continued_err(self):
        data = b"\tfoo: bar\r\n"
        with pytest.raises(exceptions.HttpSyntaxException):
            self._read(data)

    def test_read_err(self):
        data = b"foo"
        with pytest.raises(exceptions.HttpSyntaxException):
            self._read(data)

    def test_read_empty_name(self):
        data = b":foo"
        with pytest.raises(exceptions.HttpSyntaxException):
            self._read(data)

    def test_read_empty_value(self):
        data = b"bar:"
        headers = self._read(data)
        assert headers.fields == ((b"bar", b""),)


def test_read_chunked():
    req = treq(content=None)
    req.headers["Transfer-Encoding"] = "chunked"

    data = b"1\r\na\r\n0\r\n"
    with pytest.raises(exceptions.HttpSyntaxException):
        b"".join(_read_chunked(BytesIO(data)))

    data = b"1\r\na\r\n0\r\n\r\n"
    assert b"".join(_read_chunked(BytesIO(data))) == b"a"

    data = b"\r\n\r\n1\r\na\r\n1\r\nb\r\n0\r\n\r\n"
    assert b"".join(_read_chunked(BytesIO(data))) == b"ab"

    data = b"\r\n"
    with pytest.raises(Exception, match="closed prematurely"):
        b"".join(_read_chunked(BytesIO(data)))

    data = b"1\r\nfoo"
    with pytest.raises(Exception, match="Malformed chunked body"):
        b"".join(_read_chunked(BytesIO(data)))

    data = b"foo\r\nfoo"
    with pytest.raises(exceptions.HttpSyntaxException):
        b"".join(_read_chunked(BytesIO(data)))

    data = b"5\r\naaaaa\r\n0\r\n\r\n"
    with pytest.raises(Exception, match="too large"):
        b"".join(_read_chunked(BytesIO(data), limit=2))
