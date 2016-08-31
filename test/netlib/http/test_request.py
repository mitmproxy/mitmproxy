# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, division

import six

from netlib.http import Headers
from netlib.tutils import treq, raises
from .test_message import _test_decoded_attr, _test_passthrough_attr


class TestRequestData(object):
    def test_init(self):
        with raises(ValueError):
            treq(headers="foobar")

        assert isinstance(treq(headers=()).headers, Headers)


class TestRequestCore(object):
    """
    Tests for builtins and the attributes that are directly proxied from the data structure
    """
    def test_repr(self):
        request = treq()
        assert repr(request) == "Request(GET address:22/path)"
        request.host = None
        assert repr(request) == "Request(GET /path)"

    def replace(self):
        r = treq()
        r.path = b"foobarfoo"
        r.replace(b"foo", "bar")
        assert r.path == b"barbarbar"

        r.path = b"foobarfoo"
        r.replace(b"foo", "bar", count=1)
        assert r.path == b"barbarfoo"

    def test_first_line_format(self):
        _test_passthrough_attr(treq(), "first_line_format")

    def test_method(self):
        _test_decoded_attr(treq(), "method")

    def test_scheme(self):
        _test_decoded_attr(treq(), "scheme")

    def test_port(self):
        _test_passthrough_attr(treq(), "port")

    def test_path(self):
        req = treq()
        _test_decoded_attr(req, "path")
        # path can also be None.
        req.path = None
        assert req.path is None
        assert req.data.path is None

    def test_host(self):
        if six.PY2:
            from unittest import SkipTest
            raise SkipTest()

        request = treq()
        assert request.host == request.data.host.decode("idna")

        # Test IDNA encoding
        # Set str, get raw bytes
        request.host = "ídna.example"
        assert request.data.host == b"xn--dna-qma.example"
        # Set raw bytes, get decoded
        request.data.host = b"xn--idn-gla.example"
        assert request.host == "idná.example"
        # Set bytes, get raw bytes
        request.host = b"xn--dn-qia9b.example"
        assert request.data.host == b"xn--dn-qia9b.example"
        # IDNA encoding is not bijective
        request.host = "fußball"
        assert request.host == "fussball"

        # Don't fail on garbage
        request.data.host = b"foo\xFF\x00bar"
        assert request.host.startswith("foo")
        assert request.host.endswith("bar")
        # foo.bar = foo.bar should not cause any side effects.
        d = request.host
        request.host = d
        assert request.data.host == b"foo\xFF\x00bar"

    def test_host_header_update(self):
        request = treq()
        assert "host" not in request.headers
        request.host = "example.com"
        assert "host" not in request.headers

        request.headers["Host"] = "foo"
        request.host = "example.org"
        assert request.headers["Host"] == "example.org"


class TestRequestUtils(object):
    """
    Tests for additional convenience methods.
    """
    def test_url(self):
        request = treq()
        assert request.url == "http://address:22/path"

        request.url = "https://otheraddress:42/foo"
        assert request.scheme == "https"
        assert request.host == "otheraddress"
        assert request.port == 42
        assert request.path == "/foo"

        with raises(ValueError):
            request.url = "not-a-url"

    def test_url_options(self):
        request = treq(method=b"OPTIONS", path=b"*")
        assert request.url == "http://address:22"

    def test_url_authority(self):
        request = treq(first_line_format="authority")
        assert request.url == "address:22"

    def test_pretty_host(self):
        request = treq()
        # Without host header
        assert request.pretty_host == "address"
        assert request.host == "address"
        # Same port as self.port (22)
        request.headers["host"] = "other:22"
        assert request.pretty_host == "other"
        # Different ports
        request.headers["host"] = "other"
        assert request.pretty_host == "address"
        assert request.host == "address"
        # Empty host
        request.host = None
        assert request.pretty_host is None
        assert request.host is None

        # Invalid IDNA
        request.headers["host"] = ".disqus.com:22"
        assert request.pretty_host == ".disqus.com"

    def test_pretty_url(self):
        request = treq()
        # Without host header
        assert request.url == "http://address:22/path"
        assert request.pretty_url == "http://address:22/path"
        # Same port as self.port (22)
        request.headers["host"] = "other:22"
        assert request.pretty_url == "http://other:22/path"
        # Different ports
        request.headers["host"] = "other"
        assert request.pretty_url == "http://address:22/path"

    def test_pretty_url_options(self):
        request = treq(method=b"OPTIONS", path=b"*")
        assert request.pretty_url == "http://address:22"

    def test_pretty_url_authority(self):
        request = treq(first_line_format="authority")
        assert request.pretty_url == "address:22"

    def test_get_query(self):
        request = treq()
        assert not request.query

        request.url = "http://localhost:80/foo?bar=42"
        assert dict(request.query) == {"bar": "42"}

    def test_set_query(self):
        request = treq()
        assert not request.query
        request.query["foo"] = "bar"
        assert request.query["foo"] == "bar"
        assert request.path == "/path?foo=bar"

    def test_get_cookies_none(self):
        request = treq()
        request.headers = Headers()
        assert not request.cookies

    def test_get_cookies_single(self):
        request = treq()
        request.headers = Headers(cookie="cookiename=cookievalue")
        assert len(request.cookies) == 1
        assert request.cookies['cookiename'] == 'cookievalue'

    def test_get_cookies_double(self):
        request = treq()
        request.headers = Headers(cookie="cookiename=cookievalue;othercookiename=othercookievalue")
        result = request.cookies
        assert len(result) == 2
        assert result['cookiename'] == 'cookievalue'
        assert result['othercookiename'] == 'othercookievalue'

    def test_get_cookies_withequalsign(self):
        request = treq()
        request.headers = Headers(cookie="cookiename=coo=kievalue;othercookiename=othercookievalue")
        result = request.cookies
        assert len(result) == 2
        assert result['cookiename'] == 'coo=kievalue'
        assert result['othercookiename'] == 'othercookievalue'

    def test_set_cookies(self):
        request = treq()
        request.headers = Headers(cookie="cookiename=cookievalue")
        result = request.cookies
        result["cookiename"] = "foo"
        assert request.cookies["cookiename"] == "foo"

    def test_get_path_components(self):
        request = treq(path=b"/foo/bar")
        assert request.path_components == ("foo", "bar")

    def test_set_path_components(self):
        request = treq()
        request.path_components = ["foo", "baz"]
        assert request.path == "/foo/baz"

        request.path_components = []
        assert request.path == "/"

        request.path_components = ["foo", "baz"]
        request.query["hello"] = "hello"
        assert request.path_components == ("foo", "baz")

        request.path_components = ["abc"]
        assert request.path == "/abc?hello=hello"

    def test_anticache(self):
        request = treq()
        request.headers["If-Modified-Since"] = "foo"
        request.headers["If-None-Match"] = "bar"
        request.anticache()
        assert "If-Modified-Since" not in request.headers
        assert "If-None-Match" not in request.headers

    def test_anticomp(self):
        request = treq()
        request.headers["Accept-Encoding"] = "foobar"
        request.anticomp()
        assert request.headers["Accept-Encoding"] == "identity"

    def test_constrain_encoding(self):
        request = treq()

        h = request.headers.copy()
        request.constrain_encoding()  # no-op if there is no accept_encoding header.
        assert request.headers == h

        request.headers["Accept-Encoding"] = "identity, gzip, foo"
        request.constrain_encoding()
        assert "foo" not in request.headers["Accept-Encoding"]
        assert "gzip" in request.headers["Accept-Encoding"]

    def test_get_urlencoded_form(self):
        request = treq(content=b"foobar=baz")
        assert not request.urlencoded_form

        request.headers["Content-Type"] = "application/x-www-form-urlencoded"
        assert list(request.urlencoded_form.items()) == [(b"foobar", b"baz")]

    def test_set_urlencoded_form(self):
        request = treq()
        request.urlencoded_form = [(b'foo', b'bar'), (b'rab', b'oof')]
        assert request.headers["Content-Type"] == "application/x-www-form-urlencoded"
        assert request.content

    def test_get_multipart_form(self):
        request = treq(content=b"foobar")
        assert not request.multipart_form

        request.headers["Content-Type"] = "multipart/form-data"
        assert list(request.multipart_form.items()) == []
