import os
import cStringIO
from libpathod import language
from libpathod.language import base, http, websockets, writer, exceptions
import tutils


def parse_request(s):
    return language.parse_requests(s)[0]


class TestWS:
    def test_expr(self):
        v = base.WS("foo")
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

    def test_path(self):
        e = base.Path.expr()
        assert e.parseString('"/foo"')[0].value.val == "/foo"

        v = base.Path("/foo")
        assert v.value.val == "/foo"

        v = e.parseString("@100")[0]
        v2 = v.freeze({})
        v3 = v2.freeze({})
        assert v2.value.val == v3.value.val
        assert len(v2.value.val) == 100

        s = v.spec()
        assert s == v.expr().parseString(s)[0].spec()

    def test_method(self):
        e = base.Method.expr()
        assert e.parseString("get")[0].value.val == "GET"
        assert e.parseString("'foo'")[0].value.val == "foo"
        assert e.parseString("'get'")[0].value.val == "get"

        assert e.parseString("get")[0].spec() == "get"
        assert e.parseString("'foo'")[0].spec() == "'foo'"

        s = e.parseString("get")[0].spec()
        assert s == e.parseString(s)[0].spec()

        s = e.parseString("'foo'")[0].spec()
        assert s == e.parseString(s)[0].spec()

        v = e.parseString("@100")[0]
        v2 = v.freeze({})
        v3 = v2.freeze({})
        assert v2.value.val == v3.value.val

    def test_raw(self):
        e = base.Raw.expr().parseString("r")[0]
        assert e
        assert e.spec() == "r"
        assert e.freeze({}).spec() == "r"

    def test_body(self):
        e = base.Body.expr()
        v = e.parseString("b'foo'")[0]
        assert v.value.val == "foo"

        v = e.parseString("b@100")[0]
        assert str(v.value) == "@100"
        v2 = v.freeze({})
        v3 = v2.freeze({})
        assert v2.value.val == v3.value.val

        v = e.parseString("b@100g,digits", parseAll=True)[0]
        assert v.value.datatype == "digits"
        assert str(v.value) == "@100g,digits"

        s = v.spec()
        assert s == e.parseString(s)[0].spec()

    def test_pathodspec(self):
        e = base.PathodSpec.expr()
        v = e.parseString("s'200'")[0]
        assert v.value.val == "200"
        tutils.raises(
            language.ParseException,
            e.parseString,
            "s'foo'"
        )

        v = e.parseString('s"200:b@1"')[0]
        assert "@1" in v.spec()
        f = v.freeze({})
        assert "@1" not in f.spec()

    def test_pathodspec_freeze(self):
        e = base.PathodSpec(
            base.ValueLiteral(
                "200:b'foo':i10,'\\''".encode(
                    "string_escape"
                )
            )
        )
        assert e.freeze({})
        assert e.values({})

    def test_code(self):
        e = base.Code.expr()
        v = e.parseString("200")[0]
        assert v.string() == "200"
        assert v.spec() == "200"

        assert v.freeze({}).code == v.code

    def test_reason(self):
        e = base.Reason.expr()
        v = e.parseString("m'msg'")[0]
        assert v.value.val == "msg"

        s = v.spec()
        assert s == e.parseString(s)[0].spec()

        v = e.parseString("m@100")[0]
        v2 = v.freeze({})
        v3 = v2.freeze({})
        assert v2.value.val == v3.value.val


class TestHeaders:
    def test_header(self):
        e = base.Header.expr()
        v = e.parseString("h'foo'='bar'")[0]
        assert v.key.val == "foo"
        assert v.value.val == "bar"

        v2 = e.parseString(v.spec())[0]
        assert v2.key.val == v.key.val
        assert v2.value.val == v.value.val

        s = v.spec()
        assert s == e.parseString(s)[0].spec()

    def test_header_freeze(self):
        e = base.Header.expr()
        v = e.parseString("h@10=@10'")[0]
        v2 = v.freeze({})
        v3 = v2.freeze({})
        assert v2.key.val == v3.key.val
        assert v2.value.val == v3.value.val

    def test_ctype_shortcut(self):
        e = base.ShortcutContentType.expr()
        v = e.parseString("c'foo'")[0]
        assert v.key.val == "Content-Type"
        assert v.value.val == "foo"

        s = v.spec()
        assert s == e.parseString(s)[0].spec()

        e = base.ShortcutContentType.expr()
        v = e.parseString("c@100")[0]
        v2 = v.freeze({})
        v3 = v2.freeze({})
        assert v2.value.val == v3.value.val

    def test_location_shortcut(self):
        e = base.ShortcutLocation.expr()
        v = e.parseString("l'foo'")[0]
        assert v.key.val == "Location"
        assert v.value.val == "foo"

        s = v.spec()
        assert s == e.parseString(s)[0].spec()

        e = base.ShortcutLocation.expr()
        v = e.parseString("l@100")[0]
        v2 = v.freeze({})
        v3 = v2.freeze({})
        assert v2.value.val == v3.value.val

    def test_shortcuts(self):
        assert language.parse_response("400:c'foo'").headers[0].key.val == "Content-Type"
        assert language.parse_response("400:l'foo'").headers[0].key.val == "Location"

        assert 'Android' in parse_request("get:/:ua").headers[0].value.val
        assert parse_request("get:/:ua").headers[0].key.val == "User-Agent"


class TestShortcutUserAgent:
    def test_location_shortcut(self):
        e = base.ShortcutUserAgent.expr()
        v = e.parseString("ua")[0]
        assert "Android" in str(v.value)
        assert v.spec() == "ua"
        assert v.key.val == "User-Agent"

        v = e.parseString("u'foo'")[0]
        assert "foo" in str(v.value)
        assert "foo" in v.spec()

        v = e.parseString("u@100'")[0]
        assert len(str(v.freeze({}).value)) > 100
        v2 = v.freeze({})
        v3 = v2.freeze({})
        assert v2.value.val == v3.value.val


class Test_Action:
    def test_cmp(self):
        a = base.DisconnectAt(0)
        b = base.DisconnectAt(1)
        c = base.DisconnectAt(0)
        assert a < b
        assert a == c
        l = [b, a]
        l.sort()
        assert l[0].offset == 0

    def test_resolve(self):
        r = parse_request('GET:"/foo"')
        e = base.DisconnectAt("r")
        ret = e.resolve({}, r)
        assert isinstance(ret.offset, int)

    def test_repr(self):
        e = base.DisconnectAt("r")
        assert repr(e)

    def test_freeze(self):
        l = base.DisconnectAt(5)
        assert l.freeze({}).spec() == l.spec()


class TestDisconnects:
    def test_parse_response(self):
        a = language.parse_response("400:d0").actions[0]
        assert a.spec() == "d0"
        a = language.parse_response("400:dr").actions[0]
        assert a.spec() == "dr"

    def test_at(self):
        e = base.DisconnectAt.expr()
        v = e.parseString("d0")[0]
        assert isinstance(v, base.DisconnectAt)
        assert v.offset == 0

        v = e.parseString("d100")[0]
        assert v.offset == 100

        e = base.DisconnectAt.expr()
        v = e.parseString("dr")[0]
        assert v.offset == "r"

    def test_spec(self):
        assert base.DisconnectAt("r").spec() == "dr"
        assert base.DisconnectAt(10).spec() == "d10"


class TestInject:
    def test_parse_response(self):
        a = language.parse_response("400:ir,@100").actions[0]
        assert a.offset == "r"
        assert a.value.datatype == "bytes"
        assert a.value.usize == 100

        a = language.parse_response("400:ia,@100").actions[0]
        assert a.offset == "a"

    def test_at(self):
        e = base.InjectAt.expr()
        v = e.parseString("i0,'foo'")[0]
        assert v.value.val == "foo"
        assert v.offset == 0
        assert isinstance(v, base.InjectAt)

        v = e.parseString("ir,'foo'")[0]
        assert v.offset == "r"

    def test_serve(self):
        s = cStringIO.StringIO()
        r = language.parse_response("400:i0,'foo'")
        assert language.serve(r, s, {})

    def test_spec(self):
        e = base.InjectAt.expr()
        v = e.parseString("i0,'foo'")[0]
        assert v.spec() == 'i0,"foo"'

    def test_spec(self):
        e = base.InjectAt.expr()
        v = e.parseString("i0,@100")[0]
        v2 = v.freeze({})
        v3 = v2.freeze({})
        assert v2.value.val == v3.value.val


class TestPauses:
    def test_parse_response(self):
        e = base.PauseAt.expr()
        v = e.parseString("p10,10")[0]
        assert v.seconds == 10
        assert v.offset == 10

        v = e.parseString("p10,f")[0]
        assert v.seconds == "f"

        v = e.parseString("pr,f")[0]
        assert v.offset == "r"

        v = e.parseString("pa,f")[0]
        assert v.offset == "a"

    def test_request(self):
        r = language.parse_response('400:p10,10')
        assert r.actions[0].spec() == "p10,10"

    def test_spec(self):
        assert base.PauseAt("r", 5).spec() == "pr,5"
        assert base.PauseAt(0, 5).spec() == "p0,5"
        assert base.PauseAt(0, "f").spec() == "p0,f"

    def test_freeze(self):
        l = base.PauseAt("r", 5)
        assert l.freeze({}).spec() == l.spec()
