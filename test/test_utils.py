import json
from libmproxy import utils
import tutils

utils.CERT_SLEEP_TIME = 0


def test_format_timestamp():
    assert utils.format_timestamp(utils.timestamp())


def test_isBin():
    assert not utils.isBin("testing\n\r")
    assert utils.isBin("testing\x01")
    assert utils.isBin("testing\x0e")
    assert utils.isBin("testing\x7f")


def test_isXml():
    assert not utils.isXML("foo")
    assert utils.isXML("<foo")
    assert utils.isXML("  \n<foo")


def test_del_all():
    d = dict(a=1, b=2, c=3)
    utils.del_all(d, ["a", "x", "b"])
    assert d.keys() == ["c"]


def test_clean_hanging_newline():
    s = "foo\n"
    assert utils.clean_hanging_newline(s) == "foo"
    assert utils.clean_hanging_newline("foo") == "foo"


def test_pretty_size():
    assert utils.pretty_size(100) == "100B"
    assert utils.pretty_size(1024) == "1kB"
    assert utils.pretty_size(1024 + (1024/2.0)) == "1.5kB"
    assert utils.pretty_size(1024*1024) == "1MB"


def test_pkg_data():
    assert utils.pkg_data.path("console")
    tutils.raises("does not exist", utils.pkg_data.path, "nonexistent")


def test_pretty_json():
    s = json.dumps({"foo": 1})
    assert utils.pretty_json(s)
    assert not utils.pretty_json("moo")


def test_urldecode():
    s = "one=two&three=four"
    assert len(utils.urldecode(s)) == 2


def test_LRUCache():
    class Foo:
        ran = False
        @utils.LRUCache(2)
        def one(self, x):
            self.ran = True
            return x

    f = Foo()
    assert f.one(1) == 1
    assert f.ran
    f.ran = False
    assert f.one(1) == 1
    assert not f.ran

    f.ran = False
    assert f.one(1) == 1
    assert not f.ran
    assert f.one(2) == 2
    assert f.one(3) == 3
    assert f.ran

    f.ran = False
    assert f.one(1) == 1
    assert f.ran

    assert len(f._cached_one) == 2
    assert len(f._cachelist_one) == 2


def test_parse_proxy_spec():
    assert not utils.parse_proxy_spec("")
    assert utils.parse_proxy_spec("http://foo.com:88") == ("http", "foo.com", 88)
    assert utils.parse_proxy_spec("http://foo.com") == ("http", "foo.com", 80)
    assert not utils.parse_proxy_spec("foo.com")
    assert not utils.parse_proxy_spec("http://")


def test_unparse_url():
    assert utils.unparse_url("http", "foo.com", 99, "") == "http://foo.com:99"
    assert utils.unparse_url("http", "foo.com", 80, "") == "http://foo.com"
    assert utils.unparse_url("https", "foo.com", 80, "") == "https://foo.com:80"
    assert utils.unparse_url("https", "foo.com", 443, "") == "https://foo.com"


def test_parse_size():
    assert not utils.parse_size("")
    assert utils.parse_size("1") == 1
    assert utils.parse_size("1k") == 1024
    assert utils.parse_size("1m") == 1024**2
    assert utils.parse_size("1g") == 1024**3
    tutils.raises(ValueError, utils.parse_size, "1f")
    tutils.raises(ValueError, utils.parse_size, "ak")


def test_parse_content_type():
    p = utils.parse_content_type
    assert p("text/html") == ("text", "html", {})
    assert p("text") == None

    v = p("text/html; charset=UTF-8")
    assert v == ('text', 'html', {'charset': 'UTF-8'})


def test_safe_subn():
    assert utils.safe_subn("foo", u"bar", "\xc2foo")


def test_urlencode():
    assert utils.urlencode([('foo','bar')])

