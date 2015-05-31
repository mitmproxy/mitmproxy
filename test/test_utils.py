import json
from libmproxy import utils
from netlib import odict
import tutils

utils.CERT_SLEEP_TIME = 0


def test_format_timestamp():
    assert utils.format_timestamp(utils.timestamp())


def test_format_timestamp_with_milli():
    assert utils.format_timestamp_with_milli(utils.timestamp())


def test_isBin():
    assert not utils.isBin("testing\n\r")
    assert utils.isBin("testing\x01")
    assert utils.isBin("testing\x0e")
    assert utils.isBin("testing\x7f")


def test_isXml():
    assert not utils.isXML("foo")
    assert utils.isXML("<foo")
    assert utils.isXML("  \n<foo")


def test_clean_hanging_newline():
    s = "foo\n"
    assert utils.clean_hanging_newline(s) == "foo"
    assert utils.clean_hanging_newline("foo") == "foo"


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


def test_multipartdecode():
    boundary = 'somefancyboundary'
    headers = odict.ODict(
        [('content-type', ('multipart/form-data; boundary=%s' % boundary))])
    content = "--{0}\n" \
              "Content-Disposition: form-data; name=\"field1\"\n\n" \
              "value1\n" \
              "--{0}\n" \
              "Content-Disposition: form-data; name=\"field2\"\n\n" \
              "value2\n" \
              "--{0}--".format(boundary)

    form = utils.multipartdecode(headers, content)

    assert len(form) == 2
    assert form[0] == ('field1', 'value1')
    assert form[1] == ('field2', 'value2')


def test_pretty_duration():
    assert utils.pretty_duration(0.00001) == "0ms"
    assert utils.pretty_duration(0.0001) == "0ms"
    assert utils.pretty_duration(0.001) == "1ms"
    assert utils.pretty_duration(0.01) == "10ms"
    assert utils.pretty_duration(0.1) == "100ms"
    assert utils.pretty_duration(1) == "1.00s"
    assert utils.pretty_duration(10) == "10.0s"
    assert utils.pretty_duration(100) == "100s"
    assert utils.pretty_duration(1000) == "1000s"
    assert utils.pretty_duration(10000) == "10000s"
    assert utils.pretty_duration(1.123) == "1.12s"
    assert utils.pretty_duration(0.123) == "123ms"


def test_LRUCache():
    cache = utils.LRUCache(2)

    class Foo:
        ran = False

        def gen(self, x):
            self.ran = True
            return x
    f = Foo()

    assert not f.ran
    assert cache.get(f.gen, 1) == 1
    assert f.ran
    f.ran = False
    assert cache.get(f.gen, 1) == 1
    assert not f.ran

    f.ran = False
    assert cache.get(f.gen, 1) == 1
    assert not f.ran
    assert cache.get(f.gen, 2) == 2
    assert cache.get(f.gen, 3) == 3
    assert f.ran

    f.ran = False
    assert cache.get(f.gen, 1) == 1
    assert f.ran

    assert len(cache.cacheList) == 2
    assert len(cache.cache) == 2


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
    assert p("text") is None

    v = p("text/html; charset=UTF-8")
    assert v == ('text', 'html', {'charset': 'UTF-8'})


def test_safe_subn():
    assert utils.safe_subn("foo", u"bar", "\xc2foo")


def test_urlencode():
    assert utils.urlencode([('foo', 'bar')])
