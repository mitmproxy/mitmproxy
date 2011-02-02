import cStringIO
from libmproxy import filt, proxy, utils
import libpry


class uParsing(libpry.AutoTree):
    def _dump(self, x):
        c = cStringIO.StringIO()
        x.dump(fp=c)
        assert c.getvalue()

    def test_err(self):
        assert filt.parse("~h [") is None

    def test_simple(self):
        assert not filt.parse("~b")
        assert filt.parse("~q")
        assert filt.parse("~c 10")
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


class uMatching(libpry.AutoTree):
    def req(self):
        conn = proxy.BrowserConnection("one", 2222)
        headers = utils.Headers()
        headers["header"] = ["qvalue"]
        return proxy.Request(
                    conn,
                    "host",
                    80,
                    "http",
                    "GET",
                    "/path",
                    headers,
                    "content_request"
        )

    def resp(self):
        q = self.req()
        headers = utils.Headers()
        headers["header_response"] = ["svalue"]
        return proxy.Response(
                    q,
                    200,
                    "HTTP/1.1",
                    "message",
                    headers,
                    "content_response"
                )

    def q(self, q, o):
        return filt.parse(q)(o)

    def test_fcontenttype(self):
        q = self.req()
        s = self.resp()
        assert not self.q("~t content", q)
        assert not self.q("~t content", s)

        q.headers["content-type"] = ["text/json"]
        assert self.q("~t json", q)
        assert self.q("~tq json", q)
        assert not self.q("~ts json", q)

        s.headers["content-type"] = ["text/json"]
        assert self.q("~t json", s)

        del s.headers["content-type"]
        s.request.headers["content-type"] = ["text/json"]
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

    def test_head(self):
        q = self.req()
        s = self.resp()
        assert not self.q("~h nonexistent", q)
        assert self.q("~h qvalue", q)
        assert self.q("~h header", q)
        assert self.q("~h 'header: qvalue'", q)

        assert self.q("~h 'header: qvalue'", s)
        assert self.q("~h 'header_response: svalue'", s)

        assert self.q("~hq 'header: qvalue'", s)
        assert not self.q("~hq 'header_response: svalue'", s)

        assert self.q("~hq 'header: qvalue'", q)
        assert not self.q("~hq 'header_request: svalue'", q)

        assert not self.q("~hs 'header: qvalue'", s)
        assert self.q("~hs 'header_response: svalue'", s)
        assert not self.q("~hs 'header: qvalue'", q)

    def test_body(self):
        q = self.req()
        s = self.resp()
        assert not self.q("~b nonexistent", q)
        assert self.q("~b content", q)
        assert self.q("~b response", s)
        assert self.q("~b content_request", s)

        assert self.q("~bq content", q)
        assert self.q("~bq content", s)
        assert not self.q("~bq response", q)
        assert not self.q("~bq response", s)

        assert not self.q("~bs content", q)
        assert self.q("~bs content", s)
        assert not self.q("~bs nomatch", s)
        assert not self.q("~bs response", q)
        assert self.q("~bs response", s)

    def test_url(self):
        q = self.req()
        s = self.resp()
        assert self.q("~u host", q)
        assert self.q("~u host/path", q)
        assert not self.q("~u moo/path", q)

        assert self.q("~u host", s)
        assert self.q("~u host/path", s)
        assert not self.q("~u moo/path", s)

    def test_code(self):
        q = self.req()
        s = self.resp()
        assert not self.q("~c 200", q)
        assert self.q("~c 200", s)
        assert not self.q("~c 201", s)

    def test_and(self):
        s = self.resp()
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
        assert not self.q("(~c 201 | ~h nohead) | ~q", s)

    def test_not(self):
        s = self.resp()
        assert not self.q("! ~c 200", s)
        assert self.q("! ~c 201", s)
        assert self.q("!~c 201 !~c 202", s)
        assert not self.q("!~c 201 !~c 200", s)





tests = [
    uMatching(),
    uParsing()
]
