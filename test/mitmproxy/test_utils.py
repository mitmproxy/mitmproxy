import json
from mitmproxy import utils
from . import tutils

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


def test_parse_size():
    assert not utils.parse_size("")
    assert utils.parse_size("1") == 1
    assert utils.parse_size("1k") == 1024
    assert utils.parse_size("1m") == 1024**2
    assert utils.parse_size("1g") == 1024**3
    tutils.raises(ValueError, utils.parse_size, "1f")
    tutils.raises(ValueError, utils.parse_size, "ak")
