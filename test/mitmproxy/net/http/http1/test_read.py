import pytest

from mitmproxy.http import Headers
from mitmproxy.net.http.http1.read import _read_headers
from mitmproxy.net.http.http1.read import _read_request_line
from mitmproxy.net.http.http1.read import _read_response_line
from mitmproxy.net.http.http1.read import connection_close
from mitmproxy.net.http.http1.read import expected_http_body_size
from mitmproxy.net.http.http1.read import get_header_tokens
from mitmproxy.net.http.http1.read import read_request_head
from mitmproxy.net.http.http1.read import read_response_head
from mitmproxy.test.tutils import treq
from mitmproxy.test.tutils import tresp


def test_get_header_tokens():
    headers = Headers()
    assert get_header_tokens(headers, "foo") == []
    headers["foo"] = "bar"
    assert get_header_tokens(headers, "foo") == ["bar"]
    headers["foo"] = "bar, voing"
    assert get_header_tokens(headers, "foo") == ["bar", "voing"]
    headers.set_all("foo", ["bar, voing", "oink"])
    assert get_header_tokens(headers, "foo") == ["bar", "voing", "oink"]


def test_connection_close():
    headers = Headers()
    assert connection_close(b"HTTP/1.0", headers)
    assert not connection_close(b"HTTP/1.1", headers)
    assert not connection_close(b"HTTP/2.0", headers)

    headers["connection"] = "keep-alive"
    assert not connection_close(b"HTTP/1.1", headers)

    headers["connection"] = "close"
    assert connection_close(b"HTTP/1.1", headers)

    headers["connection"] = "foobar"
    assert connection_close(b"HTTP/1.0", headers)
    assert not connection_close(b"HTTP/1.1", headers)


def test_read_request_head():
    rfile = [
        b"GET / HTTP/1.1\r\n",
        b"Content-Length: 4\r\n",
    ]
    r = read_request_head(rfile)
    assert r.method == "GET"
    assert r.headers["Content-Length"] == "4"
    assert r.content is None


def test_read_response_head():
    rfile = [
        b"HTTP/1.1 418 I'm a teapot\r\n",
        b"Content-Length: 4\r\n",
    ]
    r = read_response_head(rfile)
    assert r.status_code == 418
    assert r.headers["Content-Length"] == "4"
    assert r.content is None


def test_expected_http_body_size():
    # Expect: 100-continue
    assert (
        expected_http_body_size(
            treq(headers=Headers(expect="100-continue", content_length="42")),
        )
        == 42
    )

    # http://tools.ietf.org/html/rfc7230#section-3.3
    assert (
        expected_http_body_size(
            treq(method=b"HEAD"), tresp(headers=Headers(content_length="42"))
        )
        == 0
    )
    assert (
        expected_http_body_size(
            treq(method=b"CONNECT", headers=Headers()),
            None,
        )
        == 0
    )
    assert expected_http_body_size(treq(method=b"CONNECT"), tresp()) == 0
    for code in (100, 204, 304):
        assert expected_http_body_size(treq(), tresp(status_code=code)) == 0

    # chunked
    assert (
        expected_http_body_size(
            treq(headers=Headers(transfer_encoding="chunked")),
        )
        is None
    )
    assert (
        expected_http_body_size(
            treq(headers=Headers(transfer_encoding="gzip,\tchunked")),
        )
        is None
    )
    with pytest.raises(ValueError, match="invalid transfer-encoding header"):
        expected_http_body_size(
            treq(
                headers=Headers(transfer_encoding="chun\u212aed")
            ),  # "chunKed".lower() == "chunked"
        )
    with pytest.raises(ValueError, match="unknown transfer-encoding header"):
        expected_http_body_size(
            treq(
                headers=Headers(transfer_encoding="chun ked")
            ),  # "chunKed".lower() == "chunked"
        )
    with pytest.raises(ValueError, match="unknown transfer-encoding header"):
        expected_http_body_size(
            treq(headers=Headers(transfer_encoding="qux")),
        )
    # transfer-encoding: gzip
    assert (
        expected_http_body_size(
            treq(),
            tresp(headers=Headers(transfer_encoding="gzip")),
        )
        == -1
    )
    # requests with non-chunked transfer encoding.
    # technically invalid, but we want to maximize compatibility if validate_inbound_headers is false.
    assert (
        expected_http_body_size(
            treq(headers=Headers(transfer_encoding="identity", content_length="42")),
            None,
        )
        == 42
    )
    # Example of a misbehaving client:
    # https://github.com/tensorflow/tensorflow/blob/fd9471e7d48e8e86684c847c0e1897c76e737805/third_party/xla/xla/tsl/platform/cloud/curl_http_request.cc
    assert (
        expected_http_body_size(
            treq(headers=Headers(transfer_encoding="identity")), None
        )
        == 0
    )
    assert (
        expected_http_body_size(treq(headers=Headers(transfer_encoding="gzip")), None)
        == -1
    )

    # explicit length
    assert expected_http_body_size(treq(headers=Headers(content_length="42"))) == 42
    # invalid lengths
    with pytest.raises(ValueError):
        expected_http_body_size(treq(headers=Headers(content_length=b"foo")))
    with pytest.raises(ValueError):
        expected_http_body_size(
            treq(
                headers=Headers(
                    [(b"content-length", b"42"), (b"content-length", b"42")]
                )
            )
        )

    # no length
    assert expected_http_body_size(treq(headers=Headers())) == 0
    assert (
        expected_http_body_size(treq(headers=Headers()), tresp(headers=Headers())) == -1
    )


def test_read_request_line():
    def t(b):
        return _read_request_line(b)

    assert t(b"GET / HTTP/1.1") == ("", 0, b"GET", b"", b"", b"/", b"HTTP/1.1")
    assert t(b"OPTIONS * HTTP/1.1") == ("", 0, b"OPTIONS", b"", b"", b"*", b"HTTP/1.1")
    assert t(b"CONNECT foo:42 HTTP/1.1") == (
        "foo",
        42,
        b"CONNECT",
        b"",
        b"foo:42",
        b"",
        b"HTTP/1.1",
    )
    assert t(b"GET http://foo:42/bar HTTP/1.1") == (
        "foo",
        42,
        b"GET",
        b"http",
        b"foo:42",
        b"/bar",
        b"HTTP/1.1",
    )
    assert t(b"GET http://foo:42 HTTP/1.1") == (
        "foo",
        42,
        b"GET",
        b"http",
        b"foo:42",
        b"/",
        b"HTTP/1.1",
    )

    with pytest.raises(ValueError):
        t(b"GET / WTF/1.1")
    with pytest.raises(ValueError):
        t(b"CONNECT example.com HTTP/1.1")  # port missing
    with pytest.raises(ValueError):
        t(b"GET ws://example.com/ HTTP/1.1")  # port missing
    with pytest.raises(ValueError):
        t(b"this is not http")
    with pytest.raises(ValueError):
        t(b"")


def test_read_response_line():
    def t(b):
        return _read_response_line(b)

    assert t(b"HTTP/1.1 200 OK") == (b"HTTP/1.1", 200, b"OK")
    assert t(b"HTTP/1.1 200") == (b"HTTP/1.1", 200, b"")

    # https://github.com/mitmproxy/mitmproxy/issues/784
    assert t(b"HTTP/1.1 200 Non-Autoris\xc3\xa9") == (
        b"HTTP/1.1",
        200,
        b"Non-Autoris\xc3\xa9",
    )

    with pytest.raises(ValueError):
        assert t(b"HTTP/1.1")

    with pytest.raises(ValueError):
        t(b"HTTP/1.1 OK OK")
    with pytest.raises(ValueError):
        t(b"WTF/1.1 200 OK")
    with pytest.raises(ValueError):
        t(b"")


class TestReadHeaders:
    @staticmethod
    def _read(data):
        return _read_headers(data.splitlines(keepends=True))

    def test_read_simple(self):
        data = b"Header: one\r\nHeader2: two\r\n"
        headers = self._read(data)
        assert headers.fields == ((b"Header", b"one"), (b"Header2", b"two"))

    def test_read_multi(self):
        data = b"Header: one\r\nHeader: two\r\n"
        headers = self._read(data)
        assert headers.fields == ((b"Header", b"one"), (b"Header", b"two"))

    def test_read_continued(self):
        data = b"Header: one\r\n\ttwo\r\nHeader2: three\r\n"
        headers = self._read(data)
        assert headers.fields == ((b"Header", b"one\r\n two"), (b"Header2", b"three"))

    def test_read_continued_err(self):
        data = b"\tfoo: bar\r\n"
        with pytest.raises(ValueError):
            self._read(data)

    def test_read_err(self):
        data = b"foo"
        with pytest.raises(ValueError):
            self._read(data)

    def test_read_empty_name(self):
        data = b":foo"
        with pytest.raises(ValueError):
            self._read(data)

    def test_read_empty_value(self):
        data = b"bar:"
        headers = self._read(data)
        assert headers.fields == ((b"bar", b""),)
