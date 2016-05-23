from netlib.http import Headers
from netlib.tutils import raises


class TestHeaders(object):
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

        with raises(TypeError):
            Headers([[b"Host", u"not-bytes"]])

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

    def test_replace_simple(self):
        headers = Headers(Host="example.com", Accept="text/plain")
        replacements = headers.replace("Host: ", "X-Host: ")
        assert replacements == 1
        assert headers["X-Host"] == "example.com"
        assert "Host" not in headers
        assert headers["Accept"] == "text/plain"

    def test_replace_multi(self):
        headers = self._2host()
        headers.replace(r"Host: example\.com", r"Host: example.de")
        assert headers.get_all("Host") == ["example.de", "example.org"]

    def test_replace_remove_spacer(self):
        headers = Headers(Host="example.com")
        replacements = headers.replace(r"Host: ", "X-Host ")
        assert replacements == 0
        assert headers["Host"] == "example.com"
