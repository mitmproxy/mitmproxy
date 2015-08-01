import urlparse

from netlib import utils, odict
import tutils


def test_bidi():
    b = utils.BiDi(a=1, b=2)
    assert b.a == 1
    assert b.get_name(1) == "a"
    assert b.get_name(5) is None
    tutils.raises(AttributeError, getattr, b, "c")
    tutils.raises(ValueError, utils.BiDi, one=1, two=1)


def test_hexdump():
    assert utils.hexdump("one\0" * 10)


def test_cleanBin():
    assert utils.cleanBin("one") == "one"
    assert utils.cleanBin("\00ne") == ".ne"
    assert utils.cleanBin("\nne") == "\nne"
    assert utils.cleanBin("\nne", True) == ".ne"


def test_pretty_size():
    assert utils.pretty_size(100) == "100B"
    assert utils.pretty_size(1024) == "1kB"
    assert utils.pretty_size(1024 + (1024 / 2.0)) == "1.5kB"
    assert utils.pretty_size(1024 * 1024) == "1MB"




def test_parse_url():
    assert not utils.parse_url("")

    u = "http://foo.com:8888/test"
    s, h, po, pa = utils.parse_url(u)
    assert s == "http"
    assert h == "foo.com"
    assert po == 8888
    assert pa == "/test"

    s, h, po, pa = utils.parse_url("http://foo/bar")
    assert s == "http"
    assert h == "foo"
    assert po == 80
    assert pa == "/bar"

    s, h, po, pa = utils.parse_url("http://user:pass@foo/bar")
    assert s == "http"
    assert h == "foo"
    assert po == 80
    assert pa == "/bar"

    s, h, po, pa = utils.parse_url("http://foo")
    assert pa == "/"

    s, h, po, pa = utils.parse_url("https://foo")
    assert po == 443

    assert not utils.parse_url("https://foo:bar")
    assert not utils.parse_url("https://foo:")

    # Invalid IDNA
    assert not utils.parse_url("http://\xfafoo")
    # Invalid PATH
    assert not utils.parse_url("http:/\xc6/localhost:56121")
    # Null byte in host
    assert not utils.parse_url("http://foo\0")
    # Port out of range
    assert not utils.parse_url("http://foo:999999")
    # Invalid IPv6 URL - see http://www.ietf.org/rfc/rfc2732.txt
    assert not utils.parse_url('http://lo[calhost')


def test_unparse_url():
    assert utils.unparse_url("http", "foo.com", 99, "") == "http://foo.com:99"
    assert utils.unparse_url("http", "foo.com", 80, "") == "http://foo.com"
    assert utils.unparse_url("https", "foo.com", 80, "") == "https://foo.com:80"
    assert utils.unparse_url("https", "foo.com", 443, "") == "https://foo.com"


def test_urlencode():
    assert utils.urlencode([('foo', 'bar')])



def test_urldecode():
    s = "one=two&three=four"
    assert len(utils.urldecode(s)) == 2


def test_get_header_tokens():
    h = odict.ODictCaseless()
    assert utils.get_header_tokens(h, "foo") == []
    h["foo"] = ["bar"]
    assert utils.get_header_tokens(h, "foo") == ["bar"]
    h["foo"] = ["bar, voing"]
    assert utils.get_header_tokens(h, "foo") == ["bar", "voing"]
    h["foo"] = ["bar, voing", "oink"]
    assert utils.get_header_tokens(h, "foo") == ["bar", "voing", "oink"]
