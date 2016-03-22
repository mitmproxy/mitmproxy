from six.moves import cStringIO as StringIO

from pathod.language import actions
from pathod import language


def parse_request(s):
    return language.parse_pathoc(s).next()


def test_unique_name():
    assert not actions.PauseAt(0, "f").unique_name
    assert actions.DisconnectAt(0).unique_name


class TestDisconnects:

    def test_parse_pathod(self):
        a = language.parse_pathod("400:d0").next().actions[0]
        assert a.spec() == "d0"
        a = language.parse_pathod("400:dr").next().actions[0]
        assert a.spec() == "dr"

    def test_at(self):
        e = actions.DisconnectAt.expr()
        v = e.parseString("d0")[0]
        assert isinstance(v, actions.DisconnectAt)
        assert v.offset == 0

        v = e.parseString("d100")[0]
        assert v.offset == 100

        e = actions.DisconnectAt.expr()
        v = e.parseString("dr")[0]
        assert v.offset == "r"

    def test_spec(self):
        assert actions.DisconnectAt("r").spec() == "dr"
        assert actions.DisconnectAt(10).spec() == "d10"


class TestInject:

    def test_parse_pathod(self):
        a = language.parse_pathod("400:ir,@100").next().actions[0]
        assert a.offset == "r"
        assert a.value.datatype == "bytes"
        assert a.value.usize == 100

        a = language.parse_pathod("400:ia,@100").next().actions[0]
        assert a.offset == "a"

    def test_at(self):
        e = actions.InjectAt.expr()
        v = e.parseString("i0,'foo'")[0]
        assert v.value.val == "foo"
        assert v.offset == 0
        assert isinstance(v, actions.InjectAt)

        v = e.parseString("ir,'foo'")[0]
        assert v.offset == "r"

    def test_serve(self):
        s = StringIO()
        r = language.parse_pathod("400:i0,'foo'").next()
        assert language.serve(r, s, {})

    def test_spec(self):
        e = actions.InjectAt.expr()
        v = e.parseString("i0,'foo'")[0]
        assert v.spec() == 'i0,"foo"'

    def test_spec(self):
        e = actions.InjectAt.expr()
        v = e.parseString("i0,@100")[0]
        v2 = v.freeze({})
        v3 = v2.freeze({})
        assert v2.value.val == v3.value.val


class TestPauses:

    def test_parse_pathod(self):
        e = actions.PauseAt.expr()
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
        r = language.parse_pathod('400:p10,10').next()
        assert r.actions[0].spec() == "p10,10"

    def test_spec(self):
        assert actions.PauseAt("r", 5).spec() == "pr,5"
        assert actions.PauseAt(0, 5).spec() == "p0,5"
        assert actions.PauseAt(0, "f").spec() == "p0,f"

    def test_freeze(self):
        l = actions.PauseAt("r", 5)
        assert l.freeze({}).spec() == l.spec()


class Test_Action:

    def test_cmp(self):
        a = actions.DisconnectAt(0)
        b = actions.DisconnectAt(1)
        c = actions.DisconnectAt(0)
        assert a < b
        assert a == c
        l = sorted([b, a])
        assert l[0].offset == 0

    def test_resolve(self):
        r = parse_request('GET:"/foo"')
        e = actions.DisconnectAt("r")
        ret = e.resolve({}, r)
        assert isinstance(ret.offset, int)

    def test_repr(self):
        e = actions.DisconnectAt("r")
        assert repr(e)

    def test_freeze(self):
        l = actions.DisconnectAt(5)
        assert l.freeze({}).spec() == l.spec()
