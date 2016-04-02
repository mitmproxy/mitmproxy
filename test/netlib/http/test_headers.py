from netlib.http import Headers
from netlib.tutils import raises


class TestHeaders(object):
    def _2host(self):
        return Headers(
            [
                [b"Host", b"example.com"],
                [b"host", b"example.org"]
            ]
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

        with raises(ValueError):
            Headers([[b"Host", u"not-bytes"]])

    def test_getitem(self):
        headers = Headers(Host="example.com")
        assert headers["Host"] == "example.com"
        assert headers["host"] == "example.com"
        with raises(KeyError):
            _ = headers["Accept"]

        headers = self._2host()
        assert headers["Host"] == "example.com, example.org"

    def test_str(self):
        headers = Headers(Host="example.com")
        assert bytes(headers) == b"Host: example.com\r\n"

        headers = Headers([
            [b"Host", b"example.com"],
            [b"Accept", b"text/plain"]
        ])
        assert bytes(headers) == b"Host: example.com\r\nAccept: text/plain\r\n"

        headers = Headers()
        assert bytes(headers) == b""

    def test_setitem(self):
        headers = Headers()
        headers["Host"] = "example.com"
        assert "Host" in headers
        assert "host" in headers
        assert headers["Host"] == "example.com"

        headers["host"] = "example.org"
        assert "Host" in headers
        assert "host" in headers
        assert headers["Host"] == "example.org"

        headers["accept"] = "text/plain"
        assert len(headers) == 2
        assert "Accept" in headers
        assert "Host" in headers

        headers = self._2host()
        assert len(headers.fields) == 2
        headers["Host"] = "example.com"
        assert len(headers.fields) == 1
        assert "Host" in headers

    def test_delitem(self):
        headers = Headers(Host="example.com")
        assert len(headers) == 1
        del headers["host"]
        assert len(headers) == 0
        try:
            del headers["host"]
        except KeyError:
            assert True
        else:
            assert False

        headers = self._2host()
        del headers["Host"]
        assert len(headers) == 0

    def test_keys(self):
        headers = Headers(Host="example.com")
        assert list(headers.keys()) == ["Host"]

        headers = self._2host()
        assert list(headers.keys()) == ["Host"]

    def test_eq_ne(self):
        headers1 = Headers(Host="example.com")
        headers2 = Headers(host="example.com")
        assert not (headers1 == headers2)
        assert headers1 != headers2

        headers1 = Headers(Host="example.com")
        headers2 = Headers(Host="example.com")
        assert headers1 == headers2
        assert not (headers1 != headers2)

        assert headers1 != 42

    def test_get_all(self):
        headers = self._2host()
        assert headers.get_all("host") == ["example.com", "example.org"]
        assert headers.get_all("accept") == []

    def test_set_all(self):
        headers = Headers(Host="example.com")
        headers.set_all("Accept", ["text/plain"])
        assert len(headers) == 2
        assert "accept" in headers

        headers = self._2host()
        headers.set_all("Host", ["example.org"])
        assert headers["host"] == "example.org"

        headers.set_all("Host", ["example.org", "example.net"])
        assert headers["host"] == "example.org, example.net"

    def test_state(self):
        headers = self._2host()
        assert len(headers.get_state()) == 2
        assert headers == Headers.from_state(headers.get_state())

        headers2 = Headers()
        assert headers != headers2
        headers2.set_state(headers.get_state())
        assert headers == headers2

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
