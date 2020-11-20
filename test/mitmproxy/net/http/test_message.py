import pytest

from mitmproxy.test import tutils
from mitmproxy.net import http


def _test_passthrough_attr(message, attr):
    assert getattr(message, attr) == getattr(message.data, attr)
    setattr(message, attr, b"foo")
    assert getattr(message.data, attr) == b"foo"


def _test_decoded_attr(message, attr):
    assert getattr(message, attr) == getattr(message.data, attr).decode("utf8")
    # Set str, get raw bytes
    setattr(message, attr, "foo")
    assert getattr(message.data, attr) == b"foo"
    # Set raw bytes, get decoded
    setattr(message.data, attr, b"BAR")  # use uppercase so that we can also cover request.method
    assert getattr(message, attr) == "BAR"
    # Set bytes, get raw bytes
    setattr(message, attr, b"baz")
    assert getattr(message.data, attr) == b"baz"

    # Set UTF8
    setattr(message, attr, "Non-Autorisé")
    assert getattr(message.data, attr) == b"Non-Autoris\xc3\xa9"
    # Don't fail on garbage
    setattr(message.data, attr, b"FOO\xBF\x00BAR")
    assert getattr(message, attr).startswith("FOO")
    assert getattr(message, attr).endswith("BAR")
    # foo.bar = foo.bar should not cause any side effects.
    d = getattr(message, attr)
    setattr(message, attr, d)
    assert getattr(message.data, attr) == b"FOO\xBF\x00BAR"


class TestMessageData:
    def test_eq(self):
        data = tutils.tresp(timestamp_start=42, timestamp_end=42).data
        same = tutils.tresp(timestamp_start=42, timestamp_end=42).data
        assert data == same

        other = tutils.tresp(content=b"foo").data
        assert data != other

        assert data != 0

    def test_serializable(self):
        data1 = tutils.tresp(timestamp_start=42, timestamp_end=42).data
        data2 = tutils.tresp().data.from_state(data1.get_state())  # ResponseData.from_state()

        assert data1 == data2


class TestMessage:

    def test_init(self):
        resp = tutils.tresp()
        assert resp.data

    def test_eq_ne(self):
        resp = tutils.tresp(timestamp_start=42, timestamp_end=42)
        same = tutils.tresp(timestamp_start=42, timestamp_end=42)
        assert resp.data == same.data

        other = tutils.tresp(timestamp_start=0, timestamp_end=0)
        assert resp.data != other.data

        assert resp != 0

    def test_serializable(self):
        resp = tutils.tresp()
        resp2 = http.Response.from_state(resp.get_state())
        assert resp.data == resp2.data

    def test_content_length_update(self):
        resp = tutils.tresp()
        resp.content = b"foo"
        assert resp.data.content == b"foo"
        assert resp.headers["content-length"] == "3"
        resp.content = b""
        assert resp.data.content == b""
        assert resp.headers["content-length"] == "0"
        resp.raw_content = b"bar"
        assert resp.data.content == b"bar"
        assert resp.headers["content-length"] == "0"

    def test_headers(self):
        _test_passthrough_attr(tutils.tresp(), "headers")

    def test_timestamp_start(self):
        _test_passthrough_attr(tutils.tresp(), "timestamp_start")

    def test_timestamp_end(self):
        _test_passthrough_attr(tutils.tresp(), "timestamp_end")

    def test_http_version(self):
        _test_decoded_attr(tutils.tresp(), "http_version")
        assert tutils.tresp(http_version=b"HTTP/1.0").is_http10
        assert tutils.tresp(http_version=b"HTTP/1.1").is_http11
        assert tutils.tresp(http_version=b"HTTP/2.0").is_http2


class TestMessageContentEncoding:
    def test_simple(self):
        r = tutils.tresp()
        assert r.raw_content == b"message"
        assert "content-encoding" not in r.headers
        r.encode("gzip")

        assert r.headers["content-encoding"]
        assert r.raw_content != b"message"
        assert r.content == b"message"
        assert r.raw_content != b"message"

    def test_update_content_length_header(self):
        r = tutils.tresp()
        assert int(r.headers["content-length"]) == 7
        r.encode("gzip")
        assert int(r.headers["content-length"]) == 27
        r.decode()
        assert int(r.headers["content-length"]) == 7

    def test_modify(self):
        r = tutils.tresp()
        assert "content-encoding" not in r.headers
        r.encode("gzip")

        r.content = b"foo"
        assert r.raw_content != b"foo"
        r.decode()
        assert r.raw_content == b"foo"

        with pytest.raises(TypeError):
            r.content = "foo"

    def test_unknown_ce(self):
        r = tutils.tresp()
        r.headers["content-encoding"] = "zopfli"
        r.raw_content = b"foo"
        with pytest.raises(ValueError):
            assert r.content
        assert r.headers["content-encoding"]
        assert r.get_content(strict=False) == b"foo"

    def test_utf8_as_ce(self):
        r = tutils.tresp()
        r.headers["content-encoding"] = "utf8"
        r.raw_content = b"foo"
        with pytest.raises(ValueError):
            assert r.content
        assert r.headers["content-encoding"]
        assert r.get_content(strict=False) == b"foo"

    def test_cannot_decode(self):
        r = tutils.tresp()
        r.encode("gzip")
        r.raw_content = b"foo"
        with pytest.raises(ValueError):
            assert r.content
        assert r.headers["content-encoding"]
        assert r.get_content(strict=False) == b"foo"

        with pytest.raises(ValueError):
            r.decode()
        assert r.raw_content == b"foo"
        assert "content-encoding" in r.headers

        r.decode(strict=False)
        assert r.content == b"foo"
        assert "content-encoding" not in r.headers

    def test_none(self):
        r = tutils.tresp(content=None)
        assert r.content is None
        r.content = b"foo"
        assert r.content is not None
        r.content = None
        assert r.content is None

    def test_cannot_encode(self):
        r = tutils.tresp()
        r.encode("gzip")
        r.content = None
        assert r.headers["content-encoding"]
        assert r.raw_content is None

        r.headers["content-encoding"] = "zopfli"
        r.content = b"foo"
        assert "content-encoding" not in r.headers
        assert r.raw_content == b"foo"

        with pytest.raises(ValueError):
            r.encode("zopfli")
        assert r.raw_content == b"foo"
        assert "content-encoding" not in r.headers


class TestMessageText:
    def test_simple(self):
        r = tutils.tresp(content=b'\xfc')
        assert r.raw_content == b"\xfc"
        assert r.content == b"\xfc"
        assert r.text == "ü"

        r.encode("gzip")
        assert r.text == "ü"
        r.decode()
        assert r.text == "ü"

        r.headers["content-type"] = "text/html; charset=latin1"
        r.content = b"\xc3\xbc"
        assert r.text == "Ã¼"
        r.headers["content-type"] = "text/html; charset=utf8"
        assert r.text == "ü"

    def test_guess_json(self):
        r = tutils.tresp(content=b'"\xc3\xbc"')
        r.headers["content-type"] = "application/json"
        assert r.text == '"ü"'

    def test_guess_meta_charset(self):
        r = tutils.tresp(content=b'<meta http-equiv="content-type" '
                                 b'content="text/html;charset=gb2312">\xe6\x98\x8e\xe4\xbc\xaf')
        # "鏄庝集" is decoded form of \xe6\x98\x8e\xe4\xbc\xaf in gb18030
        assert "鏄庝集" in r.text

    def test_guess_css_charset(self):
        # @charset but not text/css
        r = tutils.tresp(content=b'@charset "gb2312";'
                                 b'#foo::before {content: "\xe6\x98\x8e\xe4\xbc\xaf"}')
        # "鏄庝集" is decoded form of \xe6\x98\x8e\xe4\xbc\xaf in gb18030
        assert "鏄庝集" not in r.text

        # @charset not at the beginning
        r = tutils.tresp(content=b'foo@charset "gb2312";'
                                 b'#foo::before {content: "\xe6\x98\x8e\xe4\xbc\xaf"}')
        r.headers["content-type"] = "text/css"
        # "鏄庝集" is decoded form of \xe6\x98\x8e\xe4\xbc\xaf in gb18030
        assert "鏄庝集" not in r.text

        # @charset and text/css
        r = tutils.tresp(content=b'@charset "gb2312";'
                                 b'#foo::before {content: "\xe6\x98\x8e\xe4\xbc\xaf"}')
        r.headers["content-type"] = "text/css"
        # "鏄庝集" is decoded form of \xe6\x98\x8e\xe4\xbc\xaf in gb18030
        assert "鏄庝集" in r.text

    def test_guess_latin_1(self):
        r = tutils.tresp(content=b"\xF0\xE2")
        assert r.text == "ðâ"

    def test_none(self):
        r = tutils.tresp(content=None)
        assert r.text is None
        r.text = "foo"
        assert r.text is not None
        r.text = None
        assert r.text is None

    def test_modify(self):
        r = tutils.tresp()

        r.text = "ü"
        assert r.raw_content == b"\xfc"

        r.headers["content-type"] = "text/html; charset=utf8"
        r.text = "ü"
        assert r.raw_content == b"\xc3\xbc"
        assert r.headers["content-length"] == "2"

    def test_unknown_ce(self):
        r = tutils.tresp()
        r.headers["content-type"] = "text/html; charset=wtf"
        r.raw_content = b"foo"
        with pytest.raises(ValueError):
            assert r.text == "foo"
        assert r.get_text(strict=False) == "foo"

    def test_cannot_decode(self):
        r = tutils.tresp()
        r.headers["content-type"] = "text/html; charset=utf8"
        r.raw_content = b"\xFF"
        with pytest.raises(ValueError):
            assert r.text

        assert r.get_text(strict=False) == '\udcff'

    def test_cannot_encode(self):
        r = tutils.tresp()
        r.content = None
        assert "content-type" not in r.headers
        assert r.raw_content is None

        r.headers["content-type"] = "text/html; charset=latin1; foo=bar"
        r.text = "☃"
        assert r.headers["content-type"] == "text/html; charset=utf-8; foo=bar"
        assert r.raw_content == b'\xe2\x98\x83'

        r.headers["content-type"] = "gibberish"
        r.text = "☃"
        assert r.headers["content-type"] == "text/plain; charset=utf-8"
        assert r.raw_content == b'\xe2\x98\x83'

        del r.headers["content-type"]
        r.text = "☃"
        assert r.headers["content-type"] == "text/plain; charset=utf-8"
        assert r.raw_content == b'\xe2\x98\x83'

        r.headers["content-type"] = "text/html; charset=latin1"
        r.text = '\udcff'
        assert r.headers["content-type"] == "text/html; charset=utf-8"
        assert r.raw_content == b"\xFF"
