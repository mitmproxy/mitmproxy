import sys
import pytest

from mitmproxy.test import tutils
from mitmproxy.net.http import url


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

    # Invalid IDNA
    with tutils.raises(ValueError):
        url.parse("http://\xfafoo")
    # Invalid PATH
    with tutils.raises(ValueError):
        url.parse("http:/\xc6/localhost:56121")
    # Null byte in host
    with tutils.raises(ValueError):
        url.parse("http://foo\0")
    # Invalid port
    with tutils.raises(ValueError):
        url.parse(b"https://foo:bar")
    # Invalid IPv6 URL - see http://www.ietf.org/rfc/rfc2732.txt
    with tutils.raises(ValueError):
        url.parse('http://lo[calhost')


@pytest.mark.skipif(sys.version_info < (3, 6), reason='requires Python 3.6 or higher')
def test_parse_port_range():
    # Port out of range
    with tutils.raises(ValueError):
        url.parse("http://foo:999999")


def test_unparse():
    assert url.unparse("http", "foo.com", 99, "") == "http://foo.com:99"
    assert url.unparse("http", "foo.com", 80, "/bar") == "http://foo.com/bar"
    assert url.unparse("https", "foo.com", 80, "") == "https://foo.com:80"
    assert url.unparse("https", "foo.com", 443, "") == "https://foo.com"


surrogates = bytes(range(256)).decode("utf8", "surrogateescape")

surrogates_quoted = (
    '%00%01%02%03%04%05%06%07%08%09%0A%0B%0C%0D%0E%0F'
    '%10%11%12%13%14%15%16%17%18%19%1A%1B%1C%1D%1E%1F'
    '%20%21%22%23%24%25%26%27%28%29%2A%2B%2C-./'
    '0123456789%3A%3B%3C%3D%3E%3F'
    '%40ABCDEFGHIJKLMNO'
    'PQRSTUVWXYZ%5B%5C%5D%5E_'
    '%60abcdefghijklmno'
    'pqrstuvwxyz%7B%7C%7D%7E%7F'
    '%80%81%82%83%84%85%86%87%88%89%8A%8B%8C%8D%8E%8F'
    '%90%91%92%93%94%95%96%97%98%99%9A%9B%9C%9D%9E%9F'
    '%A0%A1%A2%A3%A4%A5%A6%A7%A8%A9%AA%AB%AC%AD%AE%AF'
    '%B0%B1%B2%B3%B4%B5%B6%B7%B8%B9%BA%BB%BC%BD%BE%BF'
    '%C0%C1%C2%C3%C4%C5%C6%C7%C8%C9%CA%CB%CC%CD%CE%CF'
    '%D0%D1%D2%D3%D4%D5%D6%D7%D8%D9%DA%DB%DC%DD%DE%DF'
    '%E0%E1%E2%E3%E4%E5%E6%E7%E8%E9%EA%EB%EC%ED%EE%EF'
    '%F0%F1%F2%F3%F4%F5%F6%F7%F8%F9%FA%FB%FC%FD%FE%FF'
)


def test_encode():
    assert url.encode([('foo', 'bar')])
    assert url.encode([('foo', surrogates)])


def test_decode():
    s = "one=two&three=four"
    assert len(url.decode(s)) == 2
    assert url.decode(surrogates)


def test_quote():
    assert url.quote("foo") == "foo"
    assert url.quote("foo bar") == "foo%20bar"
    assert url.quote(surrogates) == surrogates_quoted


def test_unquote():
    assert url.unquote("foo") == "foo"
    assert url.unquote("foo%20bar") == "foo bar"
    assert url.unquote(surrogates_quoted) == surrogates
