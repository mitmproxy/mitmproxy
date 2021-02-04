import collections
import pytest

from mitmproxy.net.http.headers import Headers, parse_content_type, assemble_content_type


class TestHeaders:
    def _2host(self):
        return Headers(
            (
                (b"Host", b"example.com"),
                (b"host", b"example.org")
            )
        )

    def test_init(self):
        headers = Headers()
        assert len(headers) == 0

        headers = Headers([[b"Host", b"example.com"]])
        assert len(headers) == 1
        assert headers["Host"] == "example.com"

        headers = Headers(Host="example.com")
        assert len(headers) == 1
        assert headers["Host"] == "example.com"

        headers = Headers(
            [[b"Host", b"invalid"]],
            Host="example.com"
        )
        assert len(headers) == 1
        assert headers["Host"] == "example.com"

        headers = Headers(
            [[b"Host", b"invalid"], [b"Accept", b"text/plain"]],
            Host="example.com"
        )
        assert len(headers) == 2
        assert headers["Host"] == "example.com"
        assert headers["Accept"] == "text/plain"

        with pytest.raises(TypeError):
            Headers([[b"Host", "not-bytes"]])

    def test_set(self):
        headers = Headers()
        headers["foo"] = "1"
        headers[b"bar"] = b"2"
        headers["baz"] = b"3"
        with pytest.raises(TypeError):
            headers["foobar"] = 42
        assert len(headers) == 3

    def test_bytes(self):
        headers = Headers(Host="example.com")
        assert bytes(headers) == b"Host: example.com\r\n"

        headers = Headers([
            [b"Host", b"example.com"],
            [b"Accept", b"text/plain"]
        ])
        assert bytes(headers) == b"Host: example.com\r\nAccept: text/plain\r\n"

        headers = Headers()
        assert bytes(headers) == b""


def test_parse_content_type():
    p = parse_content_type
    assert p("text/html") == ("text", "html", {})
    assert p("text") is None

    v = p("text/html; charset=UTF-8")
    assert v == ('text', 'html', {'charset': 'UTF-8'})


def test_assemble_content_type():
    p = assemble_content_type
    assert p("text", "html", {}) == "text/html"
    assert p("text", "html", {"charset": "utf8"}) == "text/html; charset=utf8"
    assert p("text", "html", collections.OrderedDict([("charset", "utf8"), ("foo", "bar")])) == "text/html; charset=utf8; foo=bar"
