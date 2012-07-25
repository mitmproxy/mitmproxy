import os, cStringIO
from libpathod import rparse, utils
import tutils

rparse.TESTING = True


class TestMisc:
    def test_generators(self):
        v = rparse.Value.parseString("'val'")[0]
        g = v.get_generator({})
        assert g[:] == "val"

    def test_randomgenerator(self):
        g = rparse.RandomGenerator("bytes", 100)
        assert repr(g)
        assert len(g[:10]) == 10
        assert len(g[1:10]) == 9
        assert len(g[:1000]) == 100
        assert len(g[1000:1001]) == 0
        assert g[0]

    def test_literalgenerator(self):
        g = rparse.LiteralGenerator("one")
        assert repr(g)
        assert g == "one"
        assert g[:] == "one"
        assert g[1] == "n"

    def test_filegenerator(self):
        with tutils.tmpdir() as t:
            path = os.path.join(t, "foo")
            f = open(path, "w")
            f.write("x"*10000)
            f.close()
            g = rparse.FileGenerator(path)
            assert len(g) == 10000
            assert g[0] == "x"
            assert g[-1] == "x"
            assert g[0:5] == "xxxxx"
            assert repr(g)

    def test_valueliteral(self):
        v = rparse.ValueLiteral("foo")
        assert v.expr()
        assert v.val == "foo"

        v = rparse.ValueLiteral(r"foo\n")
        assert v.expr()
        assert v.val == "foo\n"
        assert repr(v)

    def test_valuenakedliteral(self):
        v = rparse.ValueNakedLiteral("foo")
        assert v.expr()
        assert repr(v)

    def test_file_value(self):
        v = rparse.Value.parseString("<'one two'")[0]
        assert str(v)
        assert v.path == "one two"

        v = rparse.Value.parseString("<path")[0]
        assert v.path == "path"

        with tutils.tmpdir() as t:
            p = os.path.join(t, "path")
            f = open(p, "w")
            f.write("x"*10000)
            f.close()

            assert v.get_generator(dict(staticdir=t))

            v = rparse.Value.parseString("<path2")[0]
            tutils.raises(rparse.FileAccessDenied, v.get_generator, dict(staticdir=t))
            tutils.raises("access disabled", v.get_generator, dict())

            v = rparse.Value.parseString("</outside")[0]
            tutils.raises("outside", v.get_generator, dict(staticdir=t))

    def test_generated_value(self):
        v = rparse.Value.parseString("@10b")[0]
        assert v.usize == 10
        assert v.unit == "b"
        assert v.bytes() == 10
        v = rparse.Value.parseString("@10")[0]
        assert v.unit == "b"
        v = rparse.Value.parseString("@10k")[0]
        assert v.bytes() == 10240
        v = rparse.Value.parseString("@10g")[0]
        assert v.bytes() == 1024**3 * 10

        v = rparse.Value.parseString("@10g,digits")[0]
        assert v.datatype == "digits"
        g = v.get_generator({})
        assert g[:100]

        v = rparse.Value.parseString("@10,digits")[0]
        assert v.unit == "b"
        assert v.datatype == "digits"

    def test_value(self):
        assert rparse.Value.parseString("'val'")[0].val == "val"
        assert rparse.Value.parseString('"val"')[0].val == "val"
        assert rparse.Value.parseString('"\'val\'"')[0].val == "'val'"

    def test_path(self):
        e = rparse.Path.expr()
        assert e.parseString('"/foo"')[0].value.val == "/foo"
        e = rparse.Path("/foo")
        assert e.value.val == "/foo"

    def test_method(self):
        e = rparse.Method.expr()
        assert e.parseString("get")[0].value.val == "GET"
        assert e.parseString("'foo'")[0].value.val == "foo"
        assert e.parseString("'get'")[0].value.val == "get"

    def test_raw(self):
        e = rparse.Raw.expr()
        assert e.parseString("r")[0]

    def test_body(self):
        e = rparse.Body.expr()
        v = e.parseString("b'foo'")[0]
        assert v.value.val == "foo"

        v = e.parseString("b@100")[0]
        assert str(v.value) == "@100b,bytes"

        v = e.parseString("b@100g,digits", parseAll=True)[0]
        assert v.value.datatype == "digits"
        assert str(v.value) == "@100g,digits"

    def test_header(self):
        e = rparse.Header.expr()
        v = e.parseString("h'foo'='bar'")[0]
        assert v.key.val == "foo"
        assert v.value.val == "bar"

    def test_code(self):
        e = rparse.Code.expr()
        v = e.parseString("200")[0]
        assert v.code == 200

        v = e.parseString("404'msg'")[0]
        assert v.code == 404
        assert v.msg.val == "msg"

        r = e.parseString("200'foo'")[0]
        assert r.msg.val == "foo"

        r = e.parseString("200'\"foo\"'")[0]
        assert r.msg.val == "\"foo\""

        r = e.parseString('200"foo"')[0]
        assert r.msg.val == "foo"

        r = e.parseString('404')[0]
        assert r.msg.val == "Not Found"

        r = e.parseString('10')[0]
        assert r.msg.val == "Unknown code"

    def test_internal_response(self):
        d = cStringIO.StringIO()
        s = rparse.PathodErrorResponse("foo")
        s.serve(d)


class TestDisconnects:
    def test_parse_response(self):
        assert (0, "disconnect") in rparse.parse_response({}, "400:d0").actions
        assert ("r", "disconnect") in rparse.parse_response({}, "400:dr").actions

    def test_at(self):
        e = rparse.DisconnectAt.expr()
        v = e.parseString("d0")[0]
        assert isinstance(v, rparse.DisconnectAt)
        assert v.value == 0

        v = e.parseString("d100")[0]
        assert v.value == 100

        e = rparse.DisconnectAt.expr()
        v = e.parseString("dr")[0]
        assert v.value == "r"


class TestInject:
    def test_parse_response(self):
        a = rparse.parse_response({}, "400:ir,@100").actions[0]
        assert a[0] == "r"
        assert a[1] == "inject"

        a = rparse.parse_response({}, "400:ia,@100").actions[0]
        assert a[0] == "a"
        assert a[1] == "inject"

    def test_at(self):
        e = rparse.InjectAt.expr()
        v = e.parseString("i0,'foo'")[0]
        assert v.value.val == "foo"
        assert v.offset == 0
        assert isinstance(v, rparse.InjectAt)

        v = e.parseString("ir,'foo'")[0]
        assert v.offset == "r"

    def test_serve(self):
        s = cStringIO.StringIO()
        r = rparse.parse_response({}, "400:i0,'foo'")
        assert r.serve(s, None)


class TestShortcuts:
    def test_parse_response(self):
        assert rparse.parse_response({}, "400:c'foo'").headers[0][0][:] == "Content-Type"
        assert rparse.parse_response({}, "400:l'foo'").headers[0][0][:] == "Location"


class TestPauses:
    def test_parse_response(self):
        e = rparse.PauseAt.expr()
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
        r = rparse.parse_response({}, '400:p10,10')
        assert r.actions[0] == (10, "pause", 10)


class TestParseRequest:
    def test_file(self):
        p = tutils.test_data.path("data")
        d = dict(staticdir=p)
        r = rparse.parse_request(d, "+request")
        assert r.path == "/foo"

    def test_err(self):
        tutils.raises(rparse.ParseException, rparse.parse_request, {}, 'GET')

    def test_simple(self):
        r = rparse.parse_request({}, 'GET:"/foo"')
        assert r.method == "GET"
        assert r.path == "/foo"
        r = rparse.parse_request({}, 'GET:/foo')
        assert r.path == "/foo"
        r = rparse.parse_request({}, 'GET:@1k')
        assert len(r.path) == 1024

    def test_render(self):
        s = cStringIO.StringIO()
        r = rparse.parse_request({}, "GET:'/foo'")
        assert r.serve(s, None, "foo.com")

    def test_str(self):
        r = rparse.parse_request({}, 'GET:"/foo"')
        assert str(r)

    def test_multiline(self):
        l = """
            GET
            "/foo"
            ir,@1
        """
        r = rparse.parse_request({}, l)
        assert r.method == "GET"
        assert r.path == "/foo"
        assert r.actions


        l = """
            GET

            "/foo



            bar"

            ir,@1
        """
        r = rparse.parse_request({}, l)
        assert r.method == "GET"
        assert r.path.s.endswith("bar")
        assert r.actions


class TestParseResponse:
    def test_parse_err(self):
        tutils.raises(rparse.ParseException, rparse.parse_response, {}, "400:msg,b:")
        try:
            rparse.parse_response({}, "400'msg':b:")
        except rparse.ParseException, v:
            assert v.marked()
            assert str(v)

    def test_parse_header(self):
        r = rparse.parse_response({}, '400:h"foo"="bar"')
        assert utils.get_header("foo", r.headers)

    def test_parse_pause_before(self):
        r = rparse.parse_response({}, "400:p0,10")
        assert (0, "pause", 10) in r.actions

    def test_parse_pause_after(self):
        r = rparse.parse_response({}, "400:pa,10")
        assert ("a", "pause", 10) in r.actions

    def test_parse_pause_random(self):
        r = rparse.parse_response({}, "400:pr,10")
        assert ("r", "pause", 10) in r.actions

    def test_parse_stress(self):
        r = rparse.parse_response({}, "400:b@100g")
        assert r.length()


class TestWriteValues:
    def test_send_chunk(self):
        v = "foobarfoobar"
        for bs in range(1, len(v)+2):
            s = cStringIO.StringIO()
            rparse.send_chunk(s, v, bs, 0, len(v))
            assert s.getvalue() == v
            for start in range(len(v)):
                for end in range(len(v)):
                    s = cStringIO.StringIO()
                    rparse.send_chunk(s, v, bs, start, end)
                    assert s.getvalue() == v[start:end]

    def test_write_values_inject(self):
        tst = "foo"

        s = cStringIO.StringIO()
        rparse.write_values(s, [tst], [(0, "inject", "aaa")], blocksize=5)
        assert s.getvalue() == "aaafoo"

        s = cStringIO.StringIO()
        rparse.write_values(s, [tst], [(1, "inject", "aaa")], blocksize=5)
        assert s.getvalue() == "faaaoo"

        s = cStringIO.StringIO()
        rparse.write_values(s, [tst], [(1, "inject", "aaa")], blocksize=5)
        assert s.getvalue() == "faaaoo"

    def test_write_values_disconnects(self):
        s = cStringIO.StringIO()
        tst = "foo"*100
        rparse.write_values(s, [tst], [(0, "disconnect")], blocksize=5)
        assert not s.getvalue()

    def test_write_values(self):
        tst = "foobarvoing"
        s = cStringIO.StringIO()
        rparse.write_values(s, [tst], [])
        assert s.getvalue() == tst

        for bs in range(1, len(tst) + 2):
            for off in range(len(tst)):
                s = cStringIO.StringIO()
                rparse.write_values(s, [tst], [(off, "disconnect")], blocksize=bs)
                assert s.getvalue() == tst[:off]

    def test_write_values_pauses(self):
        tst = "".join(str(i) for i in range(10))
        for i in range(2, 10):
            s = cStringIO.StringIO()
            rparse.write_values(s, [tst], [(2, "pause", 0), (1, "pause", 0)], blocksize=i)
            assert s.getvalue() == tst

        for i in range(2, 10):
            s = cStringIO.StringIO()
            rparse.write_values(s, [tst], [(1, "pause", 0)], blocksize=i)
            assert s.getvalue() == tst

        tst = ["".join(str(i) for i in range(10))]*5
        for i in range(2, 10):
            s = cStringIO.StringIO()
            rparse.write_values(s, tst[:], [(1, "pause", 0)], blocksize=i)
            assert s.getvalue() == "".join(tst)

    def test_write_values_after(self):
        s = cStringIO.StringIO()
        r = rparse.parse_response({}, "400:da")
        r.serve(s, None)

        s = cStringIO.StringIO()
        r = rparse.parse_response({}, "400:pa,0")
        r.serve(s, None)

        s = cStringIO.StringIO()
        r = rparse.parse_response({}, "400:ia,'xx'")
        r.serve(s, None)
        assert s.getvalue().endswith('xx')


def test_ready_actions():
    x = [(0, 5)]
    assert rparse.ready_actions(100, x) == x

    x = [("r", 5)]
    ret = rparse.ready_actions(100, x)
    assert 0 <= ret[0][0] < 100

    x = [("a", "pause", 5)]
    ret = rparse.ready_actions(100, x)
    assert ret[0][0] > 100

    x = [(1, 5), (0, 5)]
    assert rparse.ready_actions(100, x) == sorted(x)


class TestResponse:
    def dummy_response(self):
        return rparse.parse_response({}, "400'msg'")

    def test_file(self):
        p = tutils.test_data.path("data")
        d = dict(staticdir=p)
        r = rparse.parse_response(d, "+response")
        assert r.code == 202

    def test_response(self):
        r = rparse.parse_response({}, "400'msg'")
        assert r.code == 400
        assert r.msg == "msg"

        r = rparse.parse_response({}, "400'msg':b@100b")
        assert r.msg == "msg"
        assert r.body[:]
        assert str(r)

    def test_checkfunc(self):
        s = cStringIO.StringIO()
        r = rparse.parse_response({}, "400:b@100k")
        def check(req, acts):
            return "errmsg"
        assert r.serve(s, check=check)["error"] == "errmsg"

    def test_render(self):
        s = cStringIO.StringIO()
        r = rparse.parse_response({}, "400'msg'")
        assert r.serve(s, None)

    def test_raw(self):
        s = cStringIO.StringIO()
        r = rparse.parse_response({}, "400:b'foo'")
        r.serve(s, None)
        v = s.getvalue()
        assert "Content-Length" in v
        assert "Date" in v

        s = cStringIO.StringIO()
        r = rparse.parse_response({}, "400:b'foo':r")
        r.serve(s, None)
        v = s.getvalue()
        assert not "Content-Length" in v
        assert not "Date" in v

    def test_length(self):
        def testlen(x):
            s = cStringIO.StringIO()
            x.serve(s, None)
            assert x.length() == len(s.getvalue())
        testlen(rparse.parse_response({}, "400'msg'"))
        testlen(rparse.parse_response({}, "400'msg':h'foo'='bar'"))
        testlen(rparse.parse_response({}, "400'msg':h'foo'='bar':b@100b"))

    def test_effective_length(self):
        def testlen(x, actions):
            s = cStringIO.StringIO()
            x.serve(s, None)
            assert x.effective_length(actions) == len(s.getvalue())
        actions = [

        ]
        r = rparse.parse_response({}, "400'msg':b@100")

        actions = [
            (0, "disconnect"),
        ]
        r.actions = actions
        testlen(r, actions)

        actions = [
            (0, "disconnect"),
            (0, "inject", "foo")
        ]
        r.actions = actions
        testlen(r, actions)

        actions = [
            (0, "inject", "foo")
        ]
        r.actions = actions
        testlen(r, actions)

    def test_render(self):
        r = rparse.parse_response({}, "400:p0,100:dr")
        assert r.actions[0][1] == "pause"
        assert len(r.preview_safe()) == 1
        assert not r.actions[0][1] == "pause"



def test_read_file():
    tutils.raises(rparse.FileAccessDenied, rparse.read_file, {}, "=/foo")
    p = tutils.test_data.path("data")
    d = dict(staticdir=p)
    assert rparse.read_file(d, "+./file").strip() == "testfile"
    assert rparse.read_file(d, "+file").strip() == "testfile"
    tutils.raises(rparse.FileAccessDenied, rparse.read_file, d, "+./nonexistent")
    tutils.raises(rparse.FileAccessDenied, rparse.read_file, d, "+/nonexistent")

    tutils.raises(rparse.FileAccessDenied, rparse.read_file, d, "+../test_rparse.py")
    d["unconstrained_file_access"] = True
    assert rparse.read_file(d, "+../test_rparse.py")
