import copy
import os
import pytest

from mitmproxy import options
from mitmproxy import optmanager
from mitmproxy import exceptions
from mitmproxy.test import tutils


class TO(optmanager.OptManager):
    def __init__(self, one=None, two=None):
        self.one = one
        self.two = two
        super().__init__()


class TD(optmanager.OptManager):
    def __init__(self, *, one="done", two="dtwo", three="error"):
        self.one = one
        self.two = two
        self.three = three
        super().__init__()


class TD2(TD):
    def __init__(self, *, three="dthree", four="dfour", **kwargs):
        self.three = three
        self.four = four
        super().__init__(three=three, **kwargs)


class TM(optmanager.OptManager):
    def __init__(self, one="one", two=["foo"], three=None):
        self.one = one
        self.two = two
        self.three = three
        super().__init__()


def test_defaults():
    assert TD2.default("one") == "done"
    assert TD2.default("two") == "dtwo"
    assert TD2.default("three") == "dthree"
    assert TD2.default("four") == "dfour"

    o = TD2()
    assert o._defaults == {
        "one": "done",
        "two": "dtwo",
        "three": "dthree",
        "four": "dfour",
    }
    assert not o.has_changed("one")
    newvals = dict(
        one="xone",
        two="xtwo",
        three="xthree",
        four="xfour",
    )
    o.update(**newvals)
    assert o.has_changed("one")
    for k, v in newvals.items():
        assert v == getattr(o, k)
    o.reset()
    assert not o.has_changed("one")
    for k, v in o._defaults.items():
        assert v == getattr(o, k)


def test_options():
    o = TO(two="three")
    assert o.keys() == set(["one", "two"])

    assert o.one is None
    assert o.two == "three"
    o.one = "one"
    assert o.one == "one"

    with pytest.raises(TypeError):
        TO(nonexistent = "value")
    with pytest.raises(Exception, match="No such option"):
        o.nonexistent = "value"
    with pytest.raises(Exception, match="No such option"):
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
    with pytest.raises(Exception, match="No such option"):
        o.setter("nonexistent")


def test_toggler():
    o = TO(two=True)
    f = o.toggler("two")
    f()
    assert o.two is False
    f()
    assert o.two is True
    with pytest.raises(Exception, match="No such option"):
        o.toggler("nonexistent")


class Rec():
    def __init__(self):
        self.called = None

    def __call__(self, *args, **kwargs):
        self.called = (args, kwargs)


def test_subscribe():
    o = TO()
    r = Rec()
    o.subscribe(r, ["two"])
    o.one = "foo"
    assert not r.called
    o.two = "foo"
    assert r.called

    assert len(o.changed.receivers) == 1
    del r
    o.two = "bar"
    assert len(o.changed.receivers) == 0


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


def test_serialize():
    o = TD2()
    o.three = "set"
    assert "dfour" in o.serialize(None, defaults=True)

    data = o.serialize(None)
    assert "dfour" not in data

    o2 = TD2()
    o2.load(data)
    assert o2 == o

    t = """
        unknown: foo
    """
    data = o.serialize(t)
    o2 = TD2()
    o2.load(data)
    assert o2 == o

    t = "invalid: foo\ninvalid"
    with pytest.raises(Exception, match="Config error"):
        o2.load(t)

    t = "invalid"
    with pytest.raises(Exception, match="Config error"):
        o2.load(t)

    t = ""
    o2.load(t)

    with pytest.raises(exceptions.OptionsError, matches='No such option: foobar'):
        o2.load("foobar: '123'")


def test_serialize_defaults():
    o = options.Options()
    assert o.serialize(None, defaults=True)


def test_saving():
    o = TD2()
    o.three = "set"
    with tutils.tmpdir() as tdir:
        dst = os.path.join(tdir, "conf")
        o.save(dst, defaults=True)

        o2 = TD2()
        o2.load_paths(dst)
        o2.three = "foo"
        o2.save(dst, defaults=True)

        o.load_paths(dst)
        assert o.three == "foo"

        with open(dst, 'a') as f:
            f.write("foobar: '123'")
        with pytest.raises(exceptions.OptionsError, matches=''):
            o.load_paths(dst)


def test_merge():
    m = TM()
    m.merge(dict(one="two"))
    assert m.one == "two"
    m.merge(dict(one=None))
    assert m.one == "two"
    m.merge(dict(two=["bar"]))
    assert m.two == ["foo", "bar"]
