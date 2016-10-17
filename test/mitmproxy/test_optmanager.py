import copy

from mitmproxy import optmanager
from mitmproxy import exceptions
from netlib import tutils


class TO(optmanager.OptManager):
    def __init__(self, one=None, two=None):
        self.one = one
        self.two = two
        super().__init__()


def test_options():
    o = TO(two="three")
    assert o.keys() == set(["one", "two"])

    assert o.one is None
    assert o.two == "three"
    o.one = "one"
    assert o.one == "one"

    with tutils.raises(TypeError):
        TO(nonexistent = "value")
    with tutils.raises("no such option"):
        o.nonexistent = "value"
    with tutils.raises("no such option"):
        o.update(nonexistent = "value")

    rec = []

    def sub(opts, updated):
        rec.append(copy.copy(opts))

    o.changed.connect(sub)

    o.one = "ninety"
    assert len(rec) == 1
    assert rec[-1].one == "ninety"

    o.update(one="oink")
    assert len(rec) == 2
    assert rec[-1].one == "oink"


def test_setter():
    o = TO(two="three")
    f = o.setter("two")
    f("xxx")
    assert o.two == "xxx"
    with tutils.raises("no such option"):
        o.setter("nonexistent")


def test_toggler():
    o = TO(two=True)
    f = o.toggler("two")
    f()
    assert o.two is False
    f()
    assert o.two is True
    with tutils.raises("no such option"):
        o.toggler("nonexistent")


def test_rollback():
    o = TO(one="two")

    rec = []

    def sub(opts, updated):
        rec.append(copy.copy(opts))

    recerr = []

    def errsub(opts, **kwargs):
        recerr.append(kwargs)

    def err(opts, updated):
        if opts.one == "ten":
            raise exceptions.OptionsError()

    o.changed.connect(sub)
    o.changed.connect(err)
    o.errored.connect(errsub)

    o.one = "ten"
    assert isinstance(recerr[0]["exc"], exceptions.OptionsError)
    assert o.one == "two"
    assert len(rec) == 2
    assert rec[0].one == "ten"
    assert rec[1].one == "two"


def test_repr():
    assert repr(TO()) == "test.mitmproxy.test_optmanager.TO({'one': None, 'two': None})"
    assert repr(TO(one='x' * 60)) == """test.mitmproxy.test_optmanager.TO({
    'one': 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',
    'two': None
})"""
