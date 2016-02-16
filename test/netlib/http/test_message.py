# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, division

from netlib.http import decoded, Headers
from netlib.tutils import tresp, raises


def _test_passthrough_attr(message, attr):
    assert getattr(message, attr) == getattr(message.data, attr)
    setattr(message, attr, "foo")
    assert getattr(message.data, attr) == "foo"


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

    def test_content_length_update(self):
        resp = tresp()
        resp.content = b"foo"
        assert resp.data.content == b"foo"
        assert resp.headers["content-length"] == "3"
        resp.content = b""
        assert resp.data.content == b""
        assert resp.headers["content-length"] == "0"

    def test_content_basic(self):
        _test_passthrough_attr(tresp(), "content")

    def test_headers(self):
        _test_passthrough_attr(tresp(), "headers")

    def test_timestamp_start(self):
        _test_passthrough_attr(tresp(), "timestamp_start")

    def test_timestamp_end(self):
        _test_passthrough_attr(tresp(), "timestamp_end")

    def teste_http_version(self):
        _test_decoded_attr(tresp(), "http_version")


class TestDecodedDecorator(object):

    def test_simple(self):
        r = tresp()
        assert r.content == b"message"
        assert "content-encoding" not in r.headers
        assert r.encode("gzip")

        assert r.headers["content-encoding"]
        assert r.content != b"message"
        with decoded(r):
            assert "content-encoding" not in r.headers
            assert r.content == b"message"
        assert r.headers["content-encoding"]
        assert r.content != b"message"

    def test_modify(self):
        r = tresp()
        assert "content-encoding" not in r.headers
        assert r.encode("gzip")

        with decoded(r):
            r.content = b"foo"

        assert r.content != b"foo"
        r.decode()
        assert r.content == b"foo"

    def test_unknown_ce(self):
        r = tresp()
        r.headers["content-encoding"] = "zopfli"
        r.content = b"foo"
        with decoded(r):
            assert r.headers["content-encoding"]
            assert r.content == b"foo"
        assert r.headers["content-encoding"]
        assert r.content == b"foo"

    def test_cannot_decode(self):
        r = tresp()
        assert r.encode("gzip")
        r.content = b"foo"
        with decoded(r):
            assert r.headers["content-encoding"]
            assert r.content == b"foo"
        assert r.headers["content-encoding"]
        assert r.content != b"foo"
        r.decode()
        assert r.content == b"foo"

    def test_cannot_encode(self):
        r = tresp()
        assert r.encode("gzip")
        with decoded(r):
            r.content = None

        assert "content-encoding" not in r.headers
        assert r.content is None
