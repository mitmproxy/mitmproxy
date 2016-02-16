import os
from pathod import language
from pathod.language import base, exceptions
import tutils


def parse_request(s):
    return language.parse_pathoc(s).next()


def test_times():
    reqs = list(language.parse_pathoc("get:/:x5"))
    assert len(reqs) == 5
    assert not reqs[0].times


def test_caseless_literal():
    class CL(base.CaselessLiteral):
        TOK = "foo"
    v = CL("foo")
    assert v.expr()
    assert v.values(language.Settings())


class TestTokValueNakedLiteral:

    def test_expr(self):
        v = base.TokValueNakedLiteral("foo")
        assert v.expr()

    def test_spec(self):
        v = base.TokValueNakedLiteral("foo")
        assert v.spec() == repr(v) == "foo"

        v = base.TokValueNakedLiteral("f\x00oo")
        assert v.spec() == repr(v) == r"f\x00oo"


class TestTokValueLiteral:

    def test_espr(self):
        v = base.TokValueLiteral("foo")
        assert v.expr()
        assert v.val == "foo"

        v = base.TokValueLiteral("foo\n")
        assert v.expr()
        assert v.val == "foo\n"
        assert repr(v)

    def test_spec(self):
        v = base.TokValueLiteral("foo")
        assert v.spec() == r"'foo'"

        v = base.TokValueLiteral("f\x00oo")
        assert v.spec() == repr(v) == r"'f\x00oo'"

        v = base.TokValueLiteral("\"")
        assert v.spec() == repr(v) == '\'"\''

    def roundtrip(self, spec):
        e = base.TokValueLiteral.expr()
        v = base.TokValueLiteral(spec)
        v2 = e.parseString(v.spec())
        assert v.val == v2[0].val
        assert v.spec() == v2[0].spec()

    def test_roundtrip(self):
        self.roundtrip("'")
        self.roundtrip('\'')
        self.roundtrip("a")
        self.roundtrip("\"")
        # self.roundtrip("\\")
        self.roundtrip("200:b'foo':i23,'\\''")
        self.roundtrip("\a")


class TestTokValueGenerate:

    def test_basic(self):
        v = base.TokValue.parseString("@10b")[0]
        assert v.usize == 10
        assert v.unit == "b"
        assert v.bytes() == 10
        v = base.TokValue.parseString("@10")[0]
        assert v.unit == "b"
        v = base.TokValue.parseString("@10k")[0]
        assert v.bytes() == 10240
        v = base.TokValue.parseString("@10g")[0]
        assert v.bytes() == 1024 ** 3 * 10

        v = base.TokValue.parseString("@10g,digits")[0]
        assert v.datatype == "digits"
        g = v.get_generator({})
        assert g[:100]

        v = base.TokValue.parseString("@10,digits")[0]
        assert v.unit == "b"
        assert v.datatype == "digits"

    def test_spec(self):
        v = base.TokValueGenerate(1, "b", "bytes")
        assert v.spec() == repr(v) == "@1"

        v = base.TokValueGenerate(1, "k", "bytes")
        assert v.spec() == repr(v) == "@1k"

        v = base.TokValueGenerate(1, "k", "ascii")
        assert v.spec() == repr(v) == "@1k,ascii"

        v = base.TokValueGenerate(1, "b", "ascii")
        assert v.spec() == repr(v) == "@1,ascii"

    def test_freeze(self):
        v = base.TokValueGenerate(100, "b", "ascii")
        f = v.freeze(language.Settings())
        assert len(f.val) == 100


class TestTokValueFile:

    def test_file_value(self):
        v = base.TokValue.parseString("<'one two'")[0]
        assert str(v)
        assert v.path == "one two"

        v = base.TokValue.parseString("<path")[0]
        assert v.path == "path"

    def test_access_control(self):
        v = base.TokValue.parseString("<path")[0]
        with tutils.tmpdir() as t:
            p = os.path.join(t, "path")
            with open(p, "wb") as f:
                f.write("x" * 10000)

            assert v.get_generator(language.Settings(staticdir=t))

            v = base.TokValue.parseString("<path2")[0]
            tutils.raises(
                exceptions.FileAccessDenied,
                v.get_generator,
                language.Settings(staticdir=t)
            )
            tutils.raises(
                "access disabled",
                v.get_generator,
                language.Settings()
            )

            v = base.TokValue.parseString("</outside")[0]
            tutils.raises(
                "outside",
                v.get_generator,
                language.Settings(staticdir=t)
            )

    def test_spec(self):
        v = base.TokValue.parseString("<'one two'")[0]
        v2 = base.TokValue.parseString(v.spec())[0]
        assert v2.path == "one two"

    def test_freeze(self):
        v = base.TokValue.parseString("<'one two'")[0]
        v2 = v.freeze({})
        assert v2.path == v.path


class TestMisc:

    def test_generators(self):
        v = base.TokValue.parseString("'val'")[0]
        g = v.get_generator({})
        assert g[:] == "val"

    def test_value(self):
        assert base.TokValue.parseString("'val'")[0].val == "val"
        assert base.TokValue.parseString('"val"')[0].val == "val"
        assert base.TokValue.parseString('"\'val\'"')[0].val == "'val'"

    def test_value(self):
        class TT(base.Value):
            preamble = "m"
        e = TT.expr()
        v = e.parseString("m'msg'")[0]
        assert v.value.val == "msg"

        s = v.spec()
        assert s == e.parseString(s)[0].spec()

        v = e.parseString("m@100")[0]
        v2 = v.freeze({})
        v3 = v2.freeze({})
        assert v2.value.val == v3.value.val

    def test_fixedlengthvalue(self):
        class TT(base.FixedLengthValue):
            preamble = "m"
            length = 4

        e = TT.expr()
        assert e.parseString("m@4")
        tutils.raises("invalid value length", e.parseString, "m@100")
        tutils.raises("invalid value length", e.parseString, "m@1")

        with tutils.tmpdir() as t:
            p = os.path.join(t, "path")
            s = base.Settings(staticdir=t)
            with open(p, "wb") as f:
                f.write("a" * 20)
            v = e.parseString("m<path")[0]
            tutils.raises("invalid value length", v.values, s)

            p = os.path.join(t, "path")
            with open(p, "wb") as f:
                f.write("a" * 4)
            v = e.parseString("m<path")[0]
            assert v.values(s)


class TKeyValue(base.KeyValue):
    preamble = "h"

    def values(self, settings):
        return [
            self.key.get_generator(settings),
            ": ",
            self.value.get_generator(settings),
            "\r\n",
        ]


class TestKeyValue:

    def test_simple(self):
        e = TKeyValue.expr()
        v = e.parseString("h'foo'='bar'")[0]
        assert v.key.val == "foo"
        assert v.value.val == "bar"

        v2 = e.parseString(v.spec())[0]
        assert v2.key.val == v.key.val
        assert v2.value.val == v.value.val

        s = v.spec()
        assert s == e.parseString(s)[0].spec()

    def test_freeze(self):
        e = TKeyValue.expr()
        v = e.parseString("h@10=@10'")[0]
        v2 = v.freeze({})
        v3 = v2.freeze({})
        assert v2.key.val == v3.key.val
        assert v2.value.val == v3.value.val


def test_intfield():
    class TT(base.IntField):
        preamble = "t"
        names = {
            "one": 1,
            "two": 2,
            "three": 3
        }
        max = 4
    e = TT.expr()

    v = e.parseString("tone")[0]
    assert v.value == 1
    assert v.spec() == "tone"
    assert v.values(language.Settings())

    v = e.parseString("t1")[0]
    assert v.value == 1
    assert v.spec() == "t1"

    v = e.parseString("t4")[0]
    assert v.value == 4
    assert v.spec() == "t4"

    tutils.raises("can't exceed", e.parseString, "t5")


def test_options_or_value():
    class TT(base.OptionsOrValue):
        options = [
            "one",
            "two",
            "three"
        ]
    e = TT.expr()
    assert e.parseString("one")[0].value.val == "one"
    assert e.parseString("'foo'")[0].value.val == "foo"
    assert e.parseString("'get'")[0].value.val == "get"

    assert e.parseString("one")[0].spec() == "one"
    assert e.parseString("'foo'")[0].spec() == "'foo'"

    s = e.parseString("one")[0].spec()
    assert s == e.parseString(s)[0].spec()

    s = e.parseString("'foo'")[0].spec()
    assert s == e.parseString(s)[0].spec()

    v = e.parseString("@100")[0]
    v2 = v.freeze({})
    v3 = v2.freeze({})
    assert v2.value.val == v3.value.val


def test_integer():
    e = base.Integer.expr()
    v = e.parseString("200")[0]
    assert v.string() == "200"
    assert v.spec() == "200"

    assert v.freeze({}).value == v.value

    class BInt(base.Integer):
        bounds = (1, 5)

    tutils.raises("must be between", BInt, 0)
    tutils.raises("must be between", BInt, 6)
    assert BInt(5)
    assert BInt(1)
    assert BInt(3)


class TBoolean(base.Boolean):
    name = "test"


def test_unique_name():
    b = TBoolean(True)
    assert b.unique_name


class test_boolean():
    e = TBoolean.expr()
    assert e.parseString("test")[0].value
    assert not e.parseString("-test")[0].value

    def roundtrip(s):
        e = TBoolean.expr()
        s2 = e.parseString(s)[0].spec()
        v1 = e.parseString(s)[0].value
        v2 = e.parseString(s2)[0].value
        assert s == s2
        assert v1 == v2

    roundtrip("test")
    roundtrip("-test")
