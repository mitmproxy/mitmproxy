from __future__ import absolute_import, print_function, division
from mitmproxy import ctxmanager


class TestObjOne(object):
    def one(self):
        return "one"


class TestObjTwo(object):
    def two(self):
        return "two"


def test_facade():
    o = TestObjOne()
    f = ctxmanager.Facade(lambda: o)
    assert f
    assert f.one() == "one"

    o = TestObjTwo()
    assert f.two() == "two"

    o = None
    assert not f
