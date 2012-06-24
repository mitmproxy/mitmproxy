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
        g = rparse.RandomGenerator("one", 100)
        assert len(g[:10]) == 10
        assert len(g[1:10]) == 9
        assert len(g[:1000]) == 100
        assert len(g[1000:1001]) == 0
        assert g[0]

    def test_literalgenerator(self):
        g = rparse.LiteralGenerator("one")
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

    def test_valueliteral(self):
        v = rparse.ValueLiteral("foo")
        assert v.expr()
        assert str(v)

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
            tutils.raises(rparse.ServerError, v.get_generator, dict(staticdir=t))
            tutils.raises("no static directory", v.get_generator, dict())

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

    def test_method(self):
        e = rparse.Method.expr()
        assert e.parseString("get")[0].value.val == "GET"
        assert e.parseString("'foo'")[0].value.val == "foo"
        assert e.parseString("'get'")[0].value.val == "get"

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
        s = rparse.InternalResponse(400, "foo")
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

        v = e.parseString("pf,10")[0]
        assert v.seconds == "f"

        v = e.parseString("pf,r")[0]
        assert v.offset == "r"

        v = e.parseString("pf,a")[0]
        assert v.offset == "a"

    def test_request(self):
        r = rparse.parse_response({}, '400:p10,10')
        assert r.actions[0] == (10, "pause", 10)


class TestParseRequest:
    def test_err(self):
        tutils.raises(rparse.ParseException, rparse.parse_request, {}, 'GET')

    def test_simple(self):
        r = rparse.parse_request({}, 'GET:"/foo"')
        assert r.method == "GET"
        assert r.path == "/foo"


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
        r = rparse.parse_response({}, "400:p10,0")
        assert (0, "pause", 10) in r.actions

    def test_parse_pause_after(self):
        r = rparse.parse_response({}, "400:p10,a")
        assert ("a", "pause", 10) in r.actions

    def test_parse_pause_random(self):
        r = rparse.parse_response({}, "400:p10,r")
        assert ("r", "pause", 10) in r.actions

    def test_parse_stress(self):
        r = rparse.parse_response({}, "400:b@100g")
        assert r.length()


class TestWriteValues:
    def test_write_values_disconnects(self):
        s = cStringIO.StringIO()
        tst = "foo"*100
        rparse.write_values(s, [tst], [(0, "disconnect")], blocksize=5)
        assert not s.getvalue()

    def test_write_values(self):
        tst = "foo"*1025
        s = cStringIO.StringIO()
        rparse.write_values(s, [tst], [])
        assert s.getvalue() == tst

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

    def test_response(self):
        r = rparse.parse_response({}, "400'msg'")
        assert r.code == 400
        assert r.msg == "msg"

        r = rparse.parse_response({}, "400'msg':b@100b")
        assert r.msg == "msg"
        assert r.body[:]
        assert str(r)

    def test_render(self):
        s = cStringIO.StringIO()
        r = rparse.parse_response({}, "400'msg'")
        assert r.serve(s)

    def test_length(self):
        def testlen(x):
            s = cStringIO.StringIO()
            x.serve(s)
            assert x.length() == len(s.getvalue())
        testlen(rparse.parse_response({}, "400'msg'"))
        testlen(rparse.parse_response({}, "400'msg':h'foo'='bar'"))
        testlen(rparse.parse_response({}, "400'msg':h'foo'='bar':b@100b"))
