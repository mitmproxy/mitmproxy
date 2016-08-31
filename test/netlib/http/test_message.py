# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, division

import six

from netlib.tutils import tresp
from netlib import http, tutils


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


class TestMessageData(object):
    def test_eq_ne(self):
        data = tresp(timestamp_start=42, timestamp_end=42).data
        same = tresp(timestamp_start=42, timestamp_end=42).data
        assert data == same
        assert not data != same

        other = tresp(content=b"foo").data
        assert not data == other
        assert data != other

        assert data != 0


class TestMessage(object):

    def test_init(self):
        resp = tresp()
        assert resp.data

    def test_eq_ne(self):
        resp = tresp(timestamp_start=42, timestamp_end=42)
        same = tresp(timestamp_start=42, timestamp_end=42)
        assert resp == same
        assert not resp != same

        other = tresp(timestamp_start=0, timestamp_end=0)
        assert not resp == other
        assert resp != other

        assert resp != 0

    def test_serializable(self):
        resp = tresp()
        resp2 = http.Response.from_state(resp.get_state())
        assert resp == resp2

    def test_content_length_update(self):
        resp = tresp()
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
        _test_passthrough_attr(tresp(), "headers")

    def test_timestamp_start(self):
        _test_passthrough_attr(tresp(), "timestamp_start")

    def test_timestamp_end(self):
        _test_passthrough_attr(tresp(), "timestamp_end")

    def test_http_version(self):
        _test_decoded_attr(tresp(), "http_version")

    def test_replace(self):
        r = tresp()
        r.content = b"foofootoo"
        r.replace(b"foo", "gg")
        assert r.content == b"ggggtoo"

        r.content = b"foofootoo"
        r.replace(b"foo", "gg", count=1)
        assert r.content == b"ggfootoo"


class TestMessageContentEncoding(object):
    def test_simple(self):
        r = tresp()
        assert r.raw_content == b"message"
        assert "content-encoding" not in r.headers
        r.encode("gzip")

        assert r.headers["content-encoding"]
        assert r.raw_content != b"message"
        assert r.content == b"message"
        assert r.raw_content != b"message"

    def test_modify(self):
        r = tresp()
        assert "content-encoding" not in r.headers
        r.encode("gzip")

        r.content = b"foo"
        assert r.raw_content != b"foo"
        r.decode()
        assert r.raw_content == b"foo"

        with tutils.raises(TypeError):
            r.content = u"foo"

    def test_unknown_ce(self):
        r = tresp()
        r.headers["content-encoding"] = "zopfli"
        r.raw_content = b"foo"
        with tutils.raises(ValueError):
            assert r.content
        assert r.headers["content-encoding"]
        assert r.get_content(strict=False) == b"foo"

    def test_cannot_decode(self):
        r = tresp()
        r.encode("gzip")
        r.raw_content = b"foo"
        with tutils.raises(ValueError):
            assert r.content
        assert r.headers["content-encoding"]
        assert r.get_content(strict=False) == b"foo"

        with tutils.raises(ValueError):
            r.decode()
        assert r.raw_content == b"foo"
        assert "content-encoding" in r.headers

        r.decode(strict=False)
        assert r.content == b"foo"
        assert "content-encoding" not in r.headers

    def test_none(self):
        r = tresp(content=None)
        assert r.content is None
        r.content = b"foo"
        assert r.content is not None
        r.content = None
        assert r.content is None

    def test_cannot_encode(self):
        r = tresp()
        r.encode("gzip")
        r.content = None
        assert r.headers["content-encoding"]
        assert r.raw_content is None

        r.headers["content-encoding"] = "zopfli"
        r.content = b"foo"
        assert "content-encoding" not in r.headers
        assert r.raw_content == b"foo"

        with tutils.raises(ValueError):
            r.encode("zopfli")
        assert r.raw_content == b"foo"
        assert "content-encoding" not in r.headers


class TestMessageText(object):
    def test_simple(self):
        r = tresp(content=b'\xfc')
        assert r.raw_content == b"\xfc"
        assert r.content == b"\xfc"
        assert r.text == u"ü"

        r.encode("gzip")
        assert r.text == u"ü"
        r.decode()
        assert r.text == u"ü"

        r.headers["content-type"] = "text/html; charset=latin1"
        r.content = b"\xc3\xbc"
        assert r.text == u"Ã¼"
        r.headers["content-type"] = "text/html; charset=utf8"
        assert r.text == u"ü"

    def test_guess_json(self):
        r = tresp(content=b'"\xc3\xbc"')
        r.headers["content-type"] = "application/json"
        assert r.text == u'"ü"'

    def test_none(self):
        r = tresp(content=None)
        assert r.text is None
        r.text = u"foo"
        assert r.text is not None
        r.text = None
        assert r.text is None

    def test_modify(self):
        r = tresp()

        r.text = u"ü"
        assert r.raw_content == b"\xfc"

        r.headers["content-type"] = "text/html; charset=utf8"
        r.text = u"ü"
        assert r.raw_content == b"\xc3\xbc"
        assert r.headers["content-length"] == "2"

    def test_unknown_ce(self):
        r = tresp()
        r.headers["content-type"] = "text/html; charset=wtf"
        r.raw_content = b"foo"
        with tutils.raises(ValueError):
            assert r.text == u"foo"
        assert r.get_text(strict=False) == u"foo"

    def test_cannot_decode(self):
        r = tresp()
        r.headers["content-type"] = "text/html; charset=utf8"
        r.raw_content = b"\xFF"
        with tutils.raises(ValueError):
            assert r.text

        assert r.get_text(strict=False) == u'\ufffd' if six.PY2 else '\udcff'

    def test_cannot_encode(self):
        r = tresp()
        r.content = None
        assert "content-type" not in r.headers
        assert r.raw_content is None

        r.headers["content-type"] = "text/html; charset=latin1; foo=bar"
        r.text = u"☃"
        assert r.headers["content-type"] == "text/html; charset=utf-8; foo=bar"
        assert r.raw_content == b'\xe2\x98\x83'

        r.headers["content-type"] = "gibberish"
        r.text = u"☃"
        assert r.headers["content-type"] == "text/plain; charset=utf-8"
        assert r.raw_content == b'\xe2\x98\x83'

        del r.headers["content-type"]
        r.text = u"☃"
        assert r.headers["content-type"] == "text/plain; charset=utf-8"
        assert r.raw_content == b'\xe2\x98\x83'

        r.headers["content-type"] = "text/html; charset=latin1"
        r.text = u'\udcff'
        assert r.headers["content-type"] == "text/html; charset=utf-8"
        assert r.raw_content == b'\xed\xb3\xbf' if six.PY2 else b"\xFF"
