import copy
import io
import pytest
import typing
import argparse

from mitmproxy import options
from mitmproxy import optmanager
from mitmproxy import exceptions


class TO(optmanager.OptManager):
    def __init__(self):
        super().__init__()
        self.add_option("one", typing.Optional[int], None, "help")
        self.add_option("two", typing.Optional[int], 2, "help")
        self.add_option("bool", bool, False, "help")
        self.add_option("required_int", int, 2, "help")


class TD(optmanager.OptManager):
    def __init__(self):
        super().__init__()
        self.add_option("one", str, "done", "help")
        self.add_option("two", str, "dtwo", "help")


class TD2(TD):
    def __init__(self):
        super().__init__()
        self.add_option("three", str, "dthree", "help")
        self.add_option("four", str, "dfour", "help")


class TM(optmanager.OptManager):
    def __init__(self):
        super().__init__()
        self.add_option("two", typing.Sequence[str], ["foo"], "help")
        self.add_option("one", typing.Optional[str], None, "help")


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


def test_required_int():
    o = TO()
    with pytest.raises(exceptions.OptionsError):
        o.parse_setval(o._options["required_int"], None, None)


def test_deepcopy():
    o = TD()
    copy.deepcopy(o)


def test_options():
    o = TO()
    assert o.keys() == {"bool", "one", "two", "required_int"}

    assert o.one is None
    assert o.two == 2
    o.one = 1
    assert o.one == 1

    with pytest.raises(TypeError):
        TO(nonexistent = "value")
    with pytest.raises(Exception, match="Unknown options"):
        o.nonexistent = "value"
    with pytest.raises(Exception, match="Unknown options"):
        o.update(nonexistent = "value")
    assert o.update_known(nonexistent = "value") == {"nonexistent": "value"}

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


class Rec:
    def __init__(self):
        self.called = None

    def __call__(self, *args, **kwargs):
        self.called = (args, kwargs)


def test_subscribe():
    o = TO()
    r = Rec()

    # pytest.raises keeps a reference here that interferes with the cleanup test
    # further down.
    try:
        o.subscribe(r, ["unknown"])
    except exceptions.OptionsError:
        pass
    else:
        raise AssertionError

    assert len(o.changed.receivers) == 0

    o.subscribe(r, ["two"])
    o.one = 2
    assert not r.called
    o.two = 3
    assert r.called

    assert len(o.changed.receivers) == 1
    del r
    o.two = 4
    assert len(o.changed.receivers) == 0

    class binder:
        def __init__(self):
            self.o = TO()
            self.called = False
            self.o.subscribe(self.bound, ["two"])

        def bound(self, *args, **kwargs):
            self.called = True

    t = binder()
    t.o.one = 3
    assert not t.called
    t.o.two = 3
    assert t.called


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
    with pytest.raises(exceptions.OptionsError):
        o.one = 10
    assert o.one is None
    with pytest.raises(exceptions.OptionsError):
        o.bool = True
    assert o.bool is False
    assert isinstance(recerr[0]["exc"], exceptions.OptionsError)
    assert o.one is None
    assert o.bool is False
    assert len(rec) == 4
    assert rec[0].one == 10
    assert rec[1].one is None
    assert rec[2].bool is True
    assert rec[3].bool is False

    with pytest.raises(exceptions.OptionsError):
        with o.rollback({"one"}, reraise=True):
            raise exceptions.OptionsError()


def test_simple():
    assert repr(TO())
    assert "one" in TO()


def test_items():
    assert TO().items()


def test_serialize():
    def serialize(opts: optmanager.OptManager, text: str, defaults: bool = False) -> str:
        buf = io.StringIO()
        optmanager.serialize(opts, buf, text, defaults)
        return buf.getvalue()

    o = TD2()
    o.three = "set"
    assert "dfour" in serialize(o, "", defaults=True)

    data = serialize(o, "")
    assert "dfour" not in data

    o2 = TD2()
    optmanager.load(o2, data)
    assert o2 == o
    assert not o == 42

    t = """
        unknown: foo
    """
    data = serialize(o, t)
    o2 = TD2()
    optmanager.load(o2, data)
    assert o2 == o

    t = "invalid: foo\ninvalid"
    with pytest.raises(Exception, match="Config error"):
        optmanager.load(o2, t)

    t = "invalid"
    with pytest.raises(Exception, match="Config error"):
        optmanager.load(o2, t)

    t = "# a comment"
    optmanager.load(o2, t)
    optmanager.load(o2, "foobar: '123'")
    assert o2.deferred == {"foobar": "123"}

    t = ""
    optmanager.load(o2, t)
    optmanager.load(o2, "foobar: '123'")
    assert o2.deferred == {"foobar": "123"}


def test_serialize_defaults():
    o = options.Options()
    buf = io.StringIO()
    optmanager.serialize(o, buf, "", defaults=True)
    assert buf.getvalue()


def test_saving(tmpdir):
    o = TD2()
    o.three = "set"
    dst = str(tmpdir.join("conf"))
    optmanager.save(o, dst, defaults=True)

    o2 = TD2()
    optmanager.load_paths(o2, dst)
    o2.three = "foo"
    optmanager.save(o2, dst, defaults=True)

    optmanager.load_paths(o, dst)
    assert o.three == "foo"

    with open(dst, 'a') as f:
        f.write("foobar: '123'")
    optmanager.load_paths(o, dst)
    assert o.deferred == {"foobar": "123"}

    with open(dst, 'a') as f:
        f.write("'''")
    with pytest.raises(exceptions.OptionsError):
        optmanager.load_paths(o, dst)

    with open(dst, 'wb') as f:
        f.write(b"\x01\x02\x03")
    with pytest.raises(exceptions.OptionsError):
        optmanager.load_paths(o, dst)
    with pytest.raises(exceptions.OptionsError):
        optmanager.save(o, dst)

    with open(dst, 'wb') as f:
        f.write(b"\xff\xff\xff")
    with pytest.raises(exceptions.OptionsError):
        optmanager.load_paths(o, dst)
    with pytest.raises(exceptions.OptionsError):
        optmanager.save(o, dst)


def test_merge():
    m = TM()
    m.merge(dict(one="two"))
    assert m.one == "two"
    m.merge(dict(one=None))
    assert m.one == "two"
    m.merge(dict(two=["bar"]))
    assert m.two == ["foo", "bar"]


def test_option():
    o = optmanager._Option("test", int, 1, "help", None)
    assert o.current() == 1
    with pytest.raises(TypeError):
        o.set("foo")
    with pytest.raises(TypeError):
        optmanager._Option("test", str, 1, "help", None)

    o2 = optmanager._Option("test", int, 1, "help", None)
    assert o2 == o
    o2.set(5)
    assert o2 != o


def test_dump_defaults():
    o = TTypes()
    buf = io.StringIO()
    optmanager.dump_defaults(o, buf)
    assert buf.getvalue()


def test_dump_dicts():
    o = options.Options()
    assert optmanager.dump_dicts(o)
    assert optmanager.dump_dicts(o, ['http2', 'listen_port'])


class TTypes(optmanager.OptManager):
    def __init__(self):
        super().__init__()
        self.add_option("str", str, "str", "help")
        self.add_option("choices", str, "foo", "help", ["foo", "bar", "baz"])
        self.add_option("optstr", typing.Optional[str], "optstr", "help")
        self.add_option("bool", bool, False, "help")
        self.add_option("bool_on", bool, True, "help")
        self.add_option("int", int, 0, "help")
        self.add_option("optint", typing.Optional[int], 0, "help")
        self.add_option("seqstr", typing.Sequence[str], [], "help")
        self.add_option("unknown", float, 0.0, "help")


def test_make_parser():
    parser = argparse.ArgumentParser()
    opts = TTypes()
    opts.make_parser(parser, "str", short="a")
    opts.make_parser(parser, "bool", short="b")
    opts.make_parser(parser, "int", short="c")
    opts.make_parser(parser, "seqstr", short="d")
    opts.make_parser(parser, "bool_on", short="e")

    with pytest.raises(ValueError):
        opts.make_parser(parser, "unknown")

    # Nonexistent options ignore
    opts.make_parser(parser, "nonexistentxxx")


def test_set():
    opts = TTypes()

    opts.set("str=foo")
    assert opts.str == "foo"
    with pytest.raises(TypeError):
        opts.set("str")

    opts.set("optstr=foo")
    assert opts.optstr == "foo"
    opts.set("optstr")
    assert opts.optstr is None

    opts.set("bool=false")
    assert opts.bool is False
    opts.set("bool")
    assert opts.bool is True
    opts.set("bool=true")
    assert opts.bool is True
    with pytest.raises(exceptions.OptionsError):
        opts.set("bool=wobble")

    opts.set("bool=toggle")
    assert opts.bool is False
    opts.set("bool=toggle")
    assert opts.bool is True

    opts.set("int=1")
    assert opts.int == 1
    with pytest.raises(exceptions.OptionsError):
        opts.set("int=wobble")
    opts.set("optint")
    assert opts.optint is None

    assert opts.seqstr == []
    opts.set("seqstr=foo")
    assert opts.seqstr == ["foo"]
    opts.set("seqstr=foo", "seqstr=bar")
    assert opts.seqstr == ["foo", "bar"]
    opts.set("seqstr")
    assert opts.seqstr == []

    with pytest.raises(exceptions.OptionsError):
        opts.set("deferredoption=wobble")

    opts.set("deferredoption=wobble", defer=True)
    assert "deferredoption" in opts.deferred
    opts.process_deferred()
    assert "deferredoption" in opts.deferred
    opts.add_option("deferredoption", str, "default", "help")
    opts.process_deferred()
    assert "deferredoption" not in opts.deferred
    assert opts.deferredoption == "wobble"

    opts.set(*('deferredsequenceoption=a', 'deferredsequenceoption=b'), defer=True)
    assert "deferredsequenceoption" in opts.deferred
    opts.process_deferred()
    assert "deferredsequenceoption" in opts.deferred
    opts.add_option("deferredsequenceoption", typing.Sequence[str], [], "help")
    opts.process_deferred()
    assert "deferredsequenceoption" not in opts.deferred
    assert opts.deferredsequenceoption == ["a", "b"]
