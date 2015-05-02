import os
from libpathod import language
from libpathod.language import base, exceptions
import tutils


def parse_request(s):
    return language.parse_requests(s)[0]


def test_caseless_literal():
    class CL(base.CaselessLiteral):
        TOK = "foo"
    v = CL("foo")
    assert v.expr()
    assert v.values(language.Settings())


class TestValueNakedLiteral:
    def test_expr(self):
        v = base.ValueNakedLiteral("foo")
        assert v.expr()

    def test_spec(self):
        v = base.ValueNakedLiteral("foo")
        assert v.spec() == repr(v) == "foo"

        v = base.ValueNakedLiteral("f\x00oo")
        assert v.spec() == repr(v) == r"f\x00oo"


class TestValueLiteral:
    def test_espr(self):
        v = base.ValueLiteral("foo")
        assert v.expr()
        assert v.val == "foo"

        v = base.ValueLiteral("foo\n")
        assert v.expr()
        assert v.val == "foo\n"
        assert repr(v)

    def test_spec(self):
        v = base.ValueLiteral("foo")
        assert v.spec() == r"'foo'"

        v = base.ValueLiteral("f\x00oo")
        assert v.spec() == repr(v) == r"'f\x00oo'"

        v = base.ValueLiteral("\"")
        assert v.spec() == repr(v) == '\'"\''

    def roundtrip(self, spec):
        e = base.ValueLiteral.expr()
        v = base.ValueLiteral(spec)
        v2 = e.parseString(v.spec())
        assert v.val == v2[0].val
        assert v.spec() == v2[0].spec()

    def test_roundtrip(self):
        self.roundtrip("'")
        self.roundtrip('\'')
        self.roundtrip("a")
        self.roundtrip("\"")
        self.roundtrip(r"\\")
        self.roundtrip("200:b'foo':i23,'\\''")


class TestValueGenerate:
    def test_basic(self):
        v = base.Value.parseString("@10b")[0]
        assert v.usize == 10
        assert v.unit == "b"
        assert v.bytes() == 10
        v = base.Value.parseString("@10")[0]
        assert v.unit == "b"
        v = base.Value.parseString("@10k")[0]
        assert v.bytes() == 10240
        v = base.Value.parseString("@10g")[0]
        assert v.bytes() == 1024**3 * 10

        v = base.Value.parseString("@10g,digits")[0]
        assert v.datatype == "digits"
        g = v.get_generator({})
        assert g[:100]

        v = base.Value.parseString("@10,digits")[0]
        assert v.unit == "b"
        assert v.datatype == "digits"

    def test_spec(self):
        v = base.ValueGenerate(1, "b", "bytes")
        assert v.spec() == repr(v) == "@1"

        v = base.ValueGenerate(1, "k", "bytes")
        assert v.spec() == repr(v) == "@1k"

        v = base.ValueGenerate(1, "k", "ascii")
        assert v.spec() == repr(v) == "@1k,ascii"

        v = base.ValueGenerate(1, "b", "ascii")
        assert v.spec() == repr(v) == "@1,ascii"

    def test_freeze(self):
        v = base.ValueGenerate(100, "b", "ascii")
        f = v.freeze(language.Settings())
        assert len(f.val) == 100


class TestValueFile:
    def test_file_value(self):
        v = base.Value.parseString("<'one two'")[0]
        assert str(v)
        assert v.path == "one two"

        v = base.Value.parseString("<path")[0]
        assert v.path == "path"

    def test_access_control(self):
        v = base.Value.parseString("<path")[0]
        with tutils.tmpdir() as t:
            p = os.path.join(t, "path")
            with open(p, "wb") as f:
                f.write("x" * 10000)

            assert v.get_generator(language.Settings(staticdir=t))

            v = base.Value.parseString("<path2")[0]
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

            v = base.Value.parseString("</outside")[0]
            tutils.raises(
                "outside",
                v.get_generator,
                language.Settings(staticdir=t)
            )

    def test_spec(self):
        v = base.Value.parseString("<'one two'")[0]
        v2 = base.Value.parseString(v.spec())[0]
        assert v2.path == "one two"

    def test_freeze(self):
        v = base.Value.parseString("<'one two'")[0]
        v2 = v.freeze({})
        assert v2.path == v.path


class TestMisc:
    def test_generators(self):
        v = base.Value.parseString("'val'")[0]
        g = v.get_generator({})
        assert g[:] == "val"

    def test_value(self):
        assert base.Value.parseString("'val'")[0].val == "val"
        assert base.Value.parseString('"val"')[0].val == "val"
        assert base.Value.parseString('"\'val\'"')[0].val == "'val'"

    def test_simplevalue(self):
        e = base.SimpleValue.expr()
        assert e.parseString('"/foo"')[0].value.val == "/foo"

        v = base.SimpleValue("/foo")
        assert v.value.val == "/foo"

        v = e.parseString("@100")[0]
        v2 = v.freeze({})
        v3 = v2.freeze({})
        assert v2.value.val == v3.value.val
        assert len(v2.value.val) == 100

        s = v.spec()
        assert s == v.expr().parseString(s)[0].spec()

    def test_prevalue(self):
        class TT(base.PreValue):
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


def test_options_or_value():
    class TT(base.OptionsOrValue):
        options = [
            "one",
            "two",
            "three"
        ]
    e = TT.expr()
    assert e.parseString("one")[0].value.val == "ONE"
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
