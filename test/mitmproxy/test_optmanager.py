import copy
import os
import pytest
import typing

from mitmproxy import options
from mitmproxy import optmanager
from mitmproxy import exceptions
from mitmproxy.test import tutils


class TO(optmanager.OptManager):
    def __init__(self):
        super().__init__()
        self.add_option("one", None, typing.Optional[int])
        self.add_option("two", 2, typing.Optional[int])
        self.add_option("bool", False, bool)


class TD(optmanager.OptManager):
    def __init__(self):
        super().__init__()
        self.add_option("one", "done", str)
        self.add_option("two", "dtwo", str)


class TD2(TD):
    def __init__(self):
        super().__init__()
        self.add_option("three", "dthree", str)
        self.add_option("four", "dfour", str)


class TM(optmanager.OptManager):
    def __init__(self):
        super().__init__()
        self.add_option("two", ["foo"], typing.Sequence[str])
        self.add_option("one", None, typing.Optional[str])


def test_add_option():
    o = TO()
    with pytest.raises(ValueError, match="already exists"):
        o.add_option("one", None, typing.Optional[int])


def test_defaults():
    o = TD2()
    defaults = {
        "one": "done",
        "two": "dtwo",
        "three": "dthree",
        "four": "dfour",
    }
    for k, v in defaults.items():
        assert o.default(k) == v

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

    for k in o.keys():
        assert not o.has_changed(k)


def test_options():
    o = TO()
    assert o.keys() == set(["bool", "one", "two"])

    assert o.one is None
    assert o.two == 2
    o.one = 1
    assert o.one == 1

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

    o.one = 90
    assert len(rec) == 1
    assert rec[-1].one == 90

    o.update(one=3)
    assert len(rec) == 2
    assert rec[-1].one == 3


def test_setter():
    o = TO()
    f = o.setter("two")
    f(99)
    assert o.two == 99
    with pytest.raises(Exception, match="No such option"):
        o.setter("nonexistent")


def test_toggler():
    o = TO()
    f = o.toggler("bool")
    assert o.bool is False
    f()
    assert o.bool is True
    f()
    assert o.bool is False
    with pytest.raises(Exception, match="No such option"):
        o.toggler("nonexistent")

    with pytest.raises(Exception, match="boolean options"):
        o.toggler("one")


class Rec():
    def __init__(self):
        self.called = None

    def __call__(self, *args, **kwargs):
        self.called = (args, kwargs)


def test_subscribe():
    o = TO()
    r = Rec()
    o.subscribe(r, ["two"])
    o.one = 2
    assert not r.called
    o.two = 3
    assert r.called

    assert len(o.changed.receivers) == 1
    del r
    o.two = 4
    assert len(o.changed.receivers) == 0


def test_rollback():
    o = TO()

    rec = []

    def sub(opts, updated):
        rec.append(copy.copy(opts))

    recerr = []

    def errsub(opts, **kwargs):
        recerr.append(kwargs)

    def err(opts, updated):
        if opts.one == 10:
            raise exceptions.OptionsError()
        if opts.bool is True:
            raise exceptions.OptionsError()

    o.changed.connect(sub)
    o.changed.connect(err)
    o.errored.connect(errsub)

    assert o.one is None
    o.one = 10
    o.bool = True
    assert isinstance(recerr[0]["exc"], exceptions.OptionsError)
    assert o.one is None
    assert o.bool is False
    assert len(rec) == 4
    assert rec[0].one == 10
    assert rec[1].one is None
    assert rec[2].bool is True
    assert rec[3].bool is False

    with pytest.raises(exceptions.OptionsError):
        with o.rollback(set(["one"]), reraise=True):
            raise exceptions.OptionsError()


def test_simple():
    assert repr(TO())
    assert "one" in TO()


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


def test_option():
    o = optmanager._Option("test", 1, int, None, None)
    assert o.current() == 1
    with pytest.raises(TypeError):
        o.set("foo")
    with pytest.raises(TypeError):
        optmanager._Option("test", 1, str, None, None)

    o2 = optmanager._Option("test", 1, int, None, None)
    assert o2 == o
    o2.set(5)
    assert o2 != o
