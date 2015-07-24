import cStringIO
import textwrap
import binascii

from netlib import http, odict, tcp
from netlib.http import http1
from .. import tutils, tservers

def test_httperror():
    e = http.exceptions.HttpError(404, "Not found")
    assert str(e)


def test_parse_url():
    assert not http.parse_url("")

    u = "http://foo.com:8888/test"
    s, h, po, pa = http.parse_url(u)
    assert s == "http"
    assert h == "foo.com"
    assert po == 8888
    assert pa == "/test"

    s, h, po, pa = http.parse_url("http://foo/bar")
    assert s == "http"
    assert h == "foo"
    assert po == 80
    assert pa == "/bar"

    s, h, po, pa = http.parse_url("http://user:pass@foo/bar")
    assert s == "http"
    assert h == "foo"
    assert po == 80
    assert pa == "/bar"

    s, h, po, pa = http.parse_url("http://foo")
    assert pa == "/"

    s, h, po, pa = http.parse_url("https://foo")
    assert po == 443

    assert not http.parse_url("https://foo:bar")
    assert not http.parse_url("https://foo:")

    # Invalid IDNA
    assert not http.parse_url("http://\xfafoo")
    # Invalid PATH
    assert not http.parse_url("http:/\xc6/localhost:56121")
    # Null byte in host
    assert not http.parse_url("http://foo\0")
    # Port out of range
    assert not http.parse_url("http://foo:999999")
    # Invalid IPv6 URL - see http://www.ietf.org/rfc/rfc2732.txt
    assert not http.parse_url('http://lo[calhost')
