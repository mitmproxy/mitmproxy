from typing import AnyStr

import pytest

from mitmproxy.net.http import url
from mitmproxy.net.http.url import parse_authority


def test_parse():
    with pytest.raises(ValueError):
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

    with pytest.raises(ValueError):
        url.parse(b"https://foo:bar")

    # Invalid IDNA
    with pytest.raises(ValueError):
        url.parse("http://\xfafoo")
    # Invalid PATH
    with pytest.raises(ValueError):
        url.parse("http:/\xc6/localhost:56121")
    # Null byte in host
    with pytest.raises(ValueError):
        url.parse("http://foo\0")
    # Invalid IPv6 URL - see http://www.ietf.org/rfc/rfc2732.txt
    with pytest.raises(ValueError):
        url.parse('http://lo[calhost')


def test_ascii_check():
    test_url = "https://xyz.tax-edu.net?flag=selectCourse&lc_id=42825&lc_name=茅莽莽猫氓猫氓".encode()
    scheme, host, port, full_path = url.parse(test_url)
    assert scheme == b'https'
    assert host == b'xyz.tax-edu.net'
    assert port == 443
    assert full_path == b'/?flag%3DselectCourse%26lc_id%3D42825%26lc_name%3D%E8%8C%85%E8%8E%BD%E8%8E' \
                        b'%BD%E7%8C%AB%E6%B0%93%E7%8C%AB%E6%B0%93'


def test_parse_port_range():
    # Port out of range
    with pytest.raises(ValueError):
        url.parse("http://foo:999999")


def test_unparse():
    assert url.unparse("http", "foo.com", 99, "") == "http://foo.com:99"
    assert url.unparse("http", "foo.com", 80, "/bar") == "http://foo.com/bar"
    assert url.unparse("https", "foo.com", 80, "") == "https://foo.com:80"
    assert url.unparse("https", "foo.com", 443, "") == "https://foo.com"
    assert url.unparse("https", "foo.com", 443, "*") == "https://foo.com"


# We ignore the byte 126: '~' because of an incompatibility in Python 3.6 and 3.7
# In 3.6 it is escaped as %7E
# In 3.7 it stays as ASCII character '~'
# https://bugs.python.org/issue16285
surrogates = (bytes(range(0, 126)) + bytes(range(127, 256))).decode("utf8", "surrogateescape")

surrogates_quoted = (
    '%00%01%02%03%04%05%06%07%08%09%0A%0B%0C%0D%0E%0F'
    '%10%11%12%13%14%15%16%17%18%19%1A%1B%1C%1D%1E%1F'
    '%20%21%22%23%24%25%26%27%28%29%2A%2B%2C-./'
    '0123456789%3A%3B%3C%3D%3E%3F%40'
    'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    '%5B%5C%5D%5E_%60'
    'abcdefghijklmnopqrstuvwxyz'
    '%7B%7C%7D%7F'  # 7E or ~ is excluded!
    '%80%81%82%83%84%85%86%87%88%89%8A%8B%8C%8D%8E%8F'
    '%90%91%92%93%94%95%96%97%98%99%9A%9B%9C%9D%9E%9F'
    '%A0%A1%A2%A3%A4%A5%A6%A7%A8%A9%AA%AB%AC%AD%AE%AF'
    '%B0%B1%B2%B3%B4%B5%B6%B7%B8%B9%BA%BB%BC%BD%BE%BF'
    '%C0%C1%C2%C3%C4%C5%C6%C7%C8%C9%CA%CB%CC%CD%CE%CF'
    '%D0%D1%D2%D3%D4%D5%D6%D7%D8%D9%DA%DB%DC%DD%DE%DF'
    '%E0%E1%E2%E3%E4%E5%E6%E7%E8%E9%EA%EB%EC%ED%EE%EF'
    '%F0%F1%F2%F3%F4%F5%F6%F7%F8%F9%FA%FB%FC%FD%FE%FF'
)


def test_empty_key_trailing_equal_sign():
    """
    Some HTTP clients don't send trailing equal signs for parameters without assigned value, e.g. they send
        foo=bar&baz&qux=quux
    instead of
        foo=bar&baz=&qux=quux
    The respective behavior of encode() should be driven by a reference string given in similar_to parameter
    """
    reference_without_equal = "key1=val1&key2&key3=val3"
    reference_with_equal = "key1=val1&key2=&key3=val3"

    post_data_empty_key_middle = [('one', 'two'), ('emptykey', ''), ('three', 'four')]
    post_data_empty_key_end = [('one', 'two'), ('three', 'four'), ('emptykey', '')]

    assert url.encode(post_data_empty_key_middle, similar_to=reference_with_equal) == "one=two&emptykey=&three=four"
    assert url.encode(post_data_empty_key_end, similar_to=reference_with_equal) == "one=two&three=four&emptykey="
    assert url.encode(post_data_empty_key_middle, similar_to=reference_without_equal) == "one=two&emptykey&three=four"
    assert url.encode(post_data_empty_key_end, similar_to=reference_without_equal) == "one=two&three=four&emptykey"


def test_encode():
    assert url.encode([('foo', 'bar')])
    assert url.encode([('foo', surrogates)])
    assert not url.encode([], similar_to="justatext")


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


def test_hostport():
    assert url.hostport(b"https", b"foo.com", 8080) == b"foo.com:8080"


def test_default_port():
    assert url.default_port("http") == 80
    assert url.default_port(b"https") == 443
    assert url.default_port(b"qux") is None


@pytest.mark.parametrize(
    "authority,valid,out", [
        ["foo:42", True, ("foo", 42)],
        [b"foo:42", True, ("foo", 42)],
        ["127.0.0.1:443", True, ("127.0.0.1", 443)],
        ["[2001:db8:42::]:443", True, ("2001:db8:42::", 443)],
        [b"xn--aaa-pla.example:80", True, ("äaaa.example", 80)],
        [b"xn--r8jz45g.xn--zckzah:80", True, ('例え.テスト', 80)],
        ["foo", True, ("foo", None)],
        ["foo..bar", False, ("foo..bar", None)],
        ["foo:bar", False, ("foo:bar", None)],
        [b"foo:bar", False, ("foo:bar", None)],
        ["foo:999999999", False, ("foo:999999999", None)],
        [b"\xff", False, ('\udcff', None)]
    ]
)
def test_parse_authority(authority: AnyStr, valid: bool, out):
    assert parse_authority(authority, False) == out

    if valid:
        assert parse_authority(authority, True) == out
    else:
        with pytest.raises(ValueError):
            parse_authority(authority, True)
