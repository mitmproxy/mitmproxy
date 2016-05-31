from netlib import tutils
from netlib.http import url


def test_parse():
    with tutils.raises(ValueError):
        url.parse("")

    s, h, po, pa = url.parse(b"http://foo.com:8888/test")
    assert s == b"http"
    assert h == b"foo.com"
    assert po == 8888
    assert pa == b"/test"

    s, h, po, pa = url.parse("http://foo/bar")
    assert s == b"http"
    assert h == b"foo"
    assert po == 80
    assert pa == b"/bar"

    s, h, po, pa = url.parse(b"http://user:pass@foo/bar")
    assert s == b"http"
    assert h == b"foo"
    assert po == 80
    assert pa == b"/bar"

    s, h, po, pa = url.parse(b"http://foo")
    assert pa == b"/"

    s, h, po, pa = url.parse(b"https://foo")
    assert po == 443

    with tutils.raises(ValueError):
        url.parse(b"https://foo:bar")

    # Invalid IDNA
    with tutils.raises(ValueError):
        url.parse("http://\xfafoo")
    # Invalid PATH
    with tutils.raises(ValueError):
        url.parse("http:/\xc6/localhost:56121")
    # Null byte in host
    with tutils.raises(ValueError):
        url.parse("http://foo\0")
    # Port out of range
    _, _, port, _ = url.parse("http://foo:999999")
    assert port == 80
    # Invalid IPv6 URL - see http://www.ietf.org/rfc/rfc2732.txt
    with tutils.raises(ValueError):
        url.parse('http://lo[calhost')


def test_unparse():
    assert url.unparse("http", "foo.com", 99, "") == "http://foo.com:99"
    assert url.unparse("http", "foo.com", 80, "/bar") == "http://foo.com/bar"
    assert url.unparse("https", "foo.com", 80, "") == "https://foo.com:80"
    assert url.unparse("https", "foo.com", 443, "") == "https://foo.com"


def test_urlencode():
    assert url.encode([('foo', 'bar')])


def test_urldecode():
    s = "one=two&three=four"
    assert len(url.decode(s)) == 2
