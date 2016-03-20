from six.moves import cStringIO as StringIO
from mitmproxy import filt
from mitmproxy.models import Error
from mitmproxy.models import http
from netlib.http import Headers
from . import tutils


class TestParsing:

    def _dump(self, x):
        c = StringIO()
        x.dump(fp=c)
        assert c.getvalue()

    def test_parse_err(self):
        assert filt.parse("~h [") is None

    def test_simple(self):
        assert not filt.parse("~b")
        assert filt.parse("~q")
        assert filt.parse("~c 10")
        assert filt.parse("~m foobar")
        assert filt.parse("~u foobar")
        assert filt.parse("~q ~c 10")
        p = filt.parse("~q ~c 10")
        self._dump(p)
        assert len(p.lst) == 2

    def test_naked_url(self):
        a = filt.parse("foobar ~h rex")
        assert a.lst[0].expr == "foobar"
        assert a.lst[1].expr == "rex"
        self._dump(a)

    def test_quoting(self):
        a = filt.parse("~u 'foo ~u bar' ~u voing")
        assert a.lst[0].expr == "foo ~u bar"
        assert a.lst[1].expr == "voing"
        self._dump(a)

        a = filt.parse("~u foobar")
        assert a.expr == "foobar"

        a = filt.parse(r"~u 'foobar\"\''")
        assert a.expr == "foobar\"'"

        a = filt.parse(r'~u "foo \'bar"')
        assert a.expr == "foo 'bar"

    def test_nesting(self):
        a = filt.parse("(~u foobar & ~h voing)")
        assert a.lst[0].expr == "foobar"
        self._dump(a)

    def test_not(self):
        a = filt.parse("!~h test")
        assert a.itm.expr == "test"
        a = filt.parse("!(~u test & ~h bar)")
        assert a.itm.lst[0].expr == "test"
        self._dump(a)

    def test_binaryops(self):
        a = filt.parse("~u foobar | ~h voing")
        isinstance(a, filt.FOr)
        self._dump(a)

        a = filt.parse("~u foobar & ~h voing")
        isinstance(a, filt.FAnd)
        self._dump(a)

    def test_wideops(self):
        a = filt.parse("~hq 'header: qvalue'")
        assert isinstance(a, filt.FHeadRequest)
        self._dump(a)


class TestMatching:

    def req(self):
        return tutils.tflow()

    def resp(self):
        return tutils.tflow(resp=True)

    def err(self):
        return tutils.tflow(err=True)

    def q(self, q, o):
        return filt.parse(q)(o)

    def test_asset(self):
        s = self.resp()
        assert not self.q("~a", s)
        s.response.headers["content-type"] = "text/javascript"
        assert self.q("~a", s)

    def test_fcontenttype(self):
        q = self.req()
        s = self.resp()
        assert not self.q("~t content", q)
        assert not self.q("~t content", s)

        q.request.headers["content-type"] = "text/json"
        assert self.q("~t json", q)
        assert self.q("~tq json", q)
        assert not self.q("~ts json", q)

        s.response.headers["content-type"] = "text/json"
        assert self.q("~t json", s)

        del s.response.headers["content-type"]
        s.request.headers["content-type"] = "text/json"
        assert self.q("~t json", s)
        assert self.q("~tq json", s)
        assert not self.q("~ts json", s)

    def test_freq_fresp(self):
        q = self.req()
        s = self.resp()

        assert self.q("~q", q)
        assert not self.q("~q", s)

        assert not self.q("~s", q)
        assert self.q("~s", s)

    def test_ferr(self):
        e = self.err()
        assert self.q("~e", e)

    def test_head(self):
        q = self.req()
        s = self.resp()
        assert not self.q("~h nonexistent", q)
        assert self.q("~h qvalue", q)
        assert self.q("~h header", q)
        assert self.q("~h 'header: qvalue'", q)

        assert self.q("~h 'header: qvalue'", s)
        assert self.q("~h 'header-response: svalue'", s)

        assert self.q("~hq 'header: qvalue'", s)
        assert not self.q("~hq 'header-response: svalue'", s)

        assert self.q("~hq 'header: qvalue'", q)
        assert not self.q("~hq 'header-request: svalue'", q)

        assert not self.q("~hs 'header: qvalue'", s)
        assert self.q("~hs 'header-response: svalue'", s)
        assert not self.q("~hs 'header: qvalue'", q)

    def match_body(self, q, s):
        assert not self.q("~b nonexistent", q)
        assert self.q("~b content", q)
        assert self.q("~b message", s)

        assert not self.q("~bq nomatch", s)
        assert self.q("~bq content", q)
        assert self.q("~bq content", s)
        assert not self.q("~bq message", q)
        assert not self.q("~bq message", s)

        assert not self.q("~bs nomatch", s)
        assert not self.q("~bs content", q)
        assert not self.q("~bs content", s)
        assert not self.q("~bs message", q)
        assert self.q("~bs message", s)

    def test_body(self):
        q = self.req()
        s = self.resp()
        self.match_body(q, s)

        q.request.encode("gzip")
        s.request.encode("gzip")
        s.response.encode("gzip")
        self.match_body(q, s)

    def test_method(self):
        q = self.req()
        assert self.q("~m get", q)
        assert not self.q("~m post", q)

        q.request.method = "oink"
        assert not self.q("~m get", q)

    def test_domain(self):
        q = self.req()
        assert self.q("~d address", q)
        assert not self.q("~d none", q)

    def test_url(self):
        q = self.req()
        s = self.resp()
        assert self.q("~u address", q)
        assert self.q("~u address:22/path", q)
        assert not self.q("~u moo/path", q)

        assert self.q("~u address", s)
        assert self.q("~u address:22/path", s)
        assert not self.q("~u moo/path", s)

    def test_code(self):
        q = self.req()
        s = self.resp()
        assert not self.q("~c 200", q)
        assert self.q("~c 200", s)
        assert not self.q("~c 201", s)

    def test_src(self):
        q = self.req()
        assert self.q("~src address", q)
        assert not self.q("~src foobar", q)
        assert self.q("~src :22", q)
        assert not self.q("~src :99", q)
        assert self.q("~src address:22", q)

    def test_dst(self):
        q = self.req()
        q.server_conn = tutils.tserver_conn()
        assert self.q("~dst address", q)
        assert not self.q("~dst foobar", q)
        assert self.q("~dst :22", q)
        assert not self.q("~dst :99", q)
        assert self.q("~dst address:22", q)

    def test_and(self):
        s = self.resp()
        assert self.q("~c 200 & ~h head", s)
        assert self.q("~c 200 & ~h head", s)
        assert not self.q("~c 200 & ~h nohead", s)
        assert self.q("(~c 200 & ~h head) & ~b content", s)
        assert not self.q("(~c 200 & ~h head) & ~b nonexistent", s)
        assert not self.q("(~c 200 & ~h nohead) & ~b content", s)

    def test_or(self):
        s = self.resp()
        assert self.q("~c 200 | ~h nohead", s)
        assert self.q("~c 201 | ~h head", s)
        assert not self.q("~c 201 | ~h nohead", s)
        assert self.q("(~c 201 | ~h nohead) | ~s", s)

    def test_not(self):
        s = self.resp()
        assert not self.q("! ~c 200", s)
        assert self.q("! ~c 201", s)
        assert self.q("!~c 201 !~c 202", s)
        assert not self.q("!~c 201 !~c 200", s)
