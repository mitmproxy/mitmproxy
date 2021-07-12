import io
import pytest
from unittest.mock import patch
from mitmproxy.test import tflow
from mitmproxy import flowfilter, http


class TestParsing:

    def _dump(self, x):
        c = io.StringIO()
        x.dump(fp=c)
        assert c.getvalue()

    def test_parse_err(self):
        assert flowfilter.parse("~h [") is None

    def test_simple(self):
        assert not flowfilter.parse("~b")
        assert flowfilter.parse("~q")
        assert flowfilter.parse("~c 10")
        assert flowfilter.parse("~m foobar")
        assert flowfilter.parse("~u foobar")
        assert flowfilter.parse("~q ~c 10")
        assert flowfilter.parse("~replay")
        assert flowfilter.parse("~replayq")
        assert flowfilter.parse("~replays")
        assert flowfilter.parse("~comment .")
        p = flowfilter.parse("~q ~c 10")
        self._dump(p)
        assert len(p.lst) == 2

    def test_non_ascii(self):
        assert flowfilter.parse("~s шгн")

    def test_naked_url(self):
        a = flowfilter.parse("foobar ~h rex")
        assert a.lst[0].expr == "foobar"
        assert a.lst[1].expr == "rex"
        self._dump(a)

    def test_quoting(self):
        a = flowfilter.parse("~u 'foo ~u bar' ~u voing")
        assert a.lst[0].expr == "foo ~u bar"
        assert a.lst[1].expr == "voing"
        self._dump(a)

        a = flowfilter.parse("~u foobar")
        assert a.expr == "foobar"

        a = flowfilter.parse(r"~u 'foobar\"\''")
        assert a.expr == "foobar\"'"

        a = flowfilter.parse(r'~u "foo \'bar"')
        assert a.expr == "foo 'bar"

    def test_nesting(self):
        a = flowfilter.parse("(~u foobar & ~h voing)")
        assert a.lst[0].expr == "foobar"
        self._dump(a)

    def test_not(self):
        a = flowfilter.parse("!~h test")
        assert a.itm.expr == "test"
        a = flowfilter.parse("!(~u test & ~h bar)")
        assert a.itm.lst[0].expr == "test"
        self._dump(a)

    def test_binaryops(self):
        a = flowfilter.parse("~u foobar | ~h voing")
        isinstance(a, flowfilter.FOr)
        self._dump(a)

        a = flowfilter.parse("~u foobar & ~h voing")
        isinstance(a, flowfilter.FAnd)
        self._dump(a)

    def test_wideops(self):
        a = flowfilter.parse("~hq 'header: qvalue'")
        assert isinstance(a, flowfilter.FHeadRequest)
        self._dump(a)


class TestMatchingHTTPFlow:

    def req(self):
        return tflow.tflow()

    def resp(self):
        return tflow.tflow(resp=True)

    def err(self):
        return tflow.tflow(err=True)

    def q(self, q, o):
        return flowfilter.parse(q)(o)

    def test_http(self):
        s = self.req()
        assert self.q("~http", s)
        assert not self.q("~tcp", s)

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

    def test_fmarked(self):
        q = self.req()
        assert not self.q("~marked", q)
        q.marked = ":default:"
        assert self.q("~marked", q)

    def test_fmarker_char(self):
        t = tflow.tflow()
        t.marked = ":default:"
        assert not self.q("~marker X", t)
        t.marked = 'X'
        assert self.q("~marker X", t)

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

        s.response.text = 'яч'           # Cyrillic
        assert self.q("~bs яч", s)
        s.response.text = '测试'          # Chinese
        assert self.q('~bs 测试', s)
        s.response.text = 'ॐ'            # Hindi
        assert self.q('~bs ॐ', s)
        s.response.text = 'لله'           # Arabic
        assert self.q('~bs لله', s)
        s.response.text = 'θεός'          # Greek
        assert self.q('~bs θεός', s)
        s.response.text = 'לוהים'          # Hebrew
        assert self.q('~bs לוהים', s)
        s.response.text = '神'            # Japanese
        assert self.q('~bs 神', s)
        s.response.text = '하나님'         # Korean
        assert self.q('~bs 하나님', s)
        s.response.text = 'Äÿ'            # Latin
        assert self.q('~bs Äÿ', s)

        assert not self.q("~bs nomatch", s)
        assert not self.q("~bs content", q)
        assert not self.q("~bs content", s)
        assert not self.q("~bs message", q)
        s.response.text = 'message'
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

        q.request = None
        assert not self.q("~u address", q)

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
        assert self.q("~src 127.0.0.1", q)
        assert not self.q("~src foobar", q)
        assert self.q("~src :22", q)
        assert not self.q("~src :99", q)
        assert self.q("~src 127.0.0.1:22", q)

        q.client_conn.peername = None
        assert not self.q('~src address:22', q)
        q.client_conn = None
        assert not self.q('~src address:22', q)

    def test_dst(self):
        q = self.req()
        q.server_conn = tflow.tserver_conn()
        assert self.q("~dst address", q)
        assert not self.q("~dst foobar", q)
        assert self.q("~dst :22", q)
        assert not self.q("~dst :99", q)
        assert self.q("~dst address:22", q)

        q.server_conn.address = None
        assert not self.q('~dst address:22', q)
        q.server_conn = None
        assert not self.q('~dst address:22', q)

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

    def test_replay(self):
        f = tflow.tflow()
        assert not self.q("~replay", f)
        f.is_replay = "request"
        assert self.q("~replay", f)
        assert self.q("~replayq", f)
        assert not self.q("~replays", f)
        f.is_replay = "response"
        assert self.q("~replay", f)
        assert not self.q("~replayq", f)
        assert self.q("~replays", f)

    def test_metadata(self):
        f = tflow.tflow()
        f.metadata["a"] = 1
        f.metadata["b"] = "string"
        f.metadata["c"] = {"key": "value"}
        assert self.q("~meta a", f)
        assert not self.q("~meta no", f)
        assert self.q("~meta string", f)
        assert self.q("~meta key", f)
        assert self.q("~meta value", f)
        assert self.q("~meta \"b: string\"", f)
        assert self.q("~meta \"'key': 'value'\"", f)


class TestMatchingTCPFlow:

    def flow(self):
        return tflow.ttcpflow()

    def err(self):
        return tflow.ttcpflow(err=True)

    def q(self, q, o):
        return flowfilter.parse(q)(o)

    def test_tcp(self):
        f = self.flow()
        assert self.q("~tcp", f)
        assert not self.q("~http", f)
        assert not self.q("~websocket", f)

    def test_ferr(self):
        e = self.err()
        assert self.q("~e", e)

    def test_body(self):
        f = self.flow()

        # Messages sent by client or server
        assert self.q("~b hello", f)
        assert self.q("~b me", f)
        assert not self.q("~b nonexistent", f)

        # Messages sent by client
        assert self.q("~bq hello", f)
        assert not self.q("~bq me", f)
        assert not self.q("~bq nonexistent", f)

        # Messages sent by server
        assert self.q("~bs me", f)
        assert not self.q("~bs hello", f)
        assert not self.q("~bs nonexistent", f)

    def test_src(self):
        f = self.flow()
        assert self.q("~src 127.0.0.1", f)
        assert not self.q("~src foobar", f)
        assert self.q("~src :22", f)
        assert not self.q("~src :99", f)
        assert self.q("~src 127.0.0.1:22", f)

    def test_dst(self):
        f = self.flow()
        f.server_conn = tflow.tserver_conn()
        assert self.q("~dst address", f)
        assert not self.q("~dst foobar", f)
        assert self.q("~dst :22", f)
        assert not self.q("~dst :99", f)
        assert self.q("~dst address:22", f)

    def test_and(self):
        f = self.flow()
        f.server_conn = tflow.tserver_conn()
        assert self.q("~b hello & ~b me", f)
        assert not self.q("~src wrongaddress & ~b hello", f)
        assert self.q("(~src :22 & ~dst :22) & ~b hello", f)
        assert not self.q("(~src address:22 & ~dst :22) & ~b nonexistent", f)
        assert not self.q("(~src address:22 & ~dst :99) & ~b hello", f)

    def test_or(self):
        f = self.flow()
        f.server_conn = tflow.tserver_conn()
        assert self.q("~b hello | ~b me", f)
        assert self.q("~src :22 | ~b me", f)
        assert not self.q("~src :99 | ~dst :99", f)
        assert self.q("(~src :22 | ~dst :22) | ~b me", f)

    def test_not(self):
        f = self.flow()
        assert not self.q("! ~src :22", f)
        assert self.q("! ~src :99", f)
        assert self.q("!~src :99 !~src :99", f)
        assert not self.q("!~src :99 !~src :22", f)

    def test_request(self):
        f = self.flow()
        assert not self.q("~q", f)

    def test_response(self):
        f = self.flow()
        assert not self.q("~s", f)

    def test_headers(self):
        f = self.flow()
        assert not self.q("~h whatever", f)

        # Request headers
        assert not self.q("~hq whatever", f)

        # Response headers
        assert not self.q("~hs whatever", f)

    def test_content_type(self):
        f = self.flow()
        assert not self.q("~t whatever", f)

        # Request content-type
        assert not self.q("~tq whatever", f)

        # Response content-type
        assert not self.q("~ts whatever", f)

    def test_code(self):
        f = self.flow()
        assert not self.q("~c 200", f)

    def test_domain(self):
        f = self.flow()
        assert not self.q("~d whatever", f)

    def test_method(self):
        f = self.flow()
        assert not self.q("~m whatever", f)

    def test_url(self):
        f = self.flow()
        assert not self.q("~u whatever", f)


class TestMatchingWebSocketFlow:

    def flow(self) -> http.HTTPFlow:
        return tflow.twebsocketflow()

    def q(self, q, o):
        return flowfilter.parse(q)(o)

    def test_websocket(self):
        f = self.flow()
        assert self.q("~websocket", f)
        assert not self.q("~tcp", f)
        assert self.q("~http", f)

    def test_handshake(self):
        f = self.flow()
        assert self.q("~websocket", f)
        assert not self.q("~tcp", f)
        assert self.q("~http", f)

        f = tflow.tflow()
        assert not self.q("~websocket", f)
        f = tflow.tflow(resp=True)
        assert not self.q("~websocket", f)

    def test_domain(self):
        q = self.flow()
        assert self.q("~d example.com", q)
        assert not self.q("~d none", q)

    def test_url(self):
        q = self.flow()
        assert self.q("~u example.com", q)
        assert self.q("~u example.com/ws", q)
        assert not self.q("~u moo/path", q)

    def test_body(self):
        f = self.flow()

        # Messages sent by client or server
        assert self.q("~b hello", f)
        assert self.q("~b me", f)
        assert not self.q("~b nonexistent", f)

        # Messages sent by client
        assert self.q("~bq hello", f)
        assert not self.q("~bq me", f)
        assert not self.q("~bq nonexistent", f)

        # Messages sent by server
        assert self.q("~bs me", f)
        assert not self.q("~bs hello", f)
        assert not self.q("~bs nonexistent", f)

    def test_src(self):
        f = self.flow()
        assert self.q("~src 127.0.0.1", f)
        assert not self.q("~src foobar", f)
        assert self.q("~src :22", f)
        assert not self.q("~src :99", f)
        assert self.q("~src 127.0.0.1:22", f)

    def test_dst(self):
        f = self.flow()
        f.server_conn = tflow.tserver_conn()
        assert self.q("~dst address", f)
        assert not self.q("~dst foobar", f)
        assert self.q("~dst :22", f)
        assert not self.q("~dst :99", f)
        assert self.q("~dst address:22", f)

    def test_and(self):
        f = self.flow()
        f.server_conn = tflow.tserver_conn()
        assert self.q("~b hello & ~b me", f)
        assert not self.q("~src wrongaddress & ~b hello", f)
        assert self.q("(~src :22 & ~dst :22) & ~b hello", f)
        assert not self.q("(~src address:22 & ~dst :22) & ~b nonexistent", f)
        assert not self.q("(~src address:22 & ~dst :99) & ~b hello", f)

    def test_or(self):
        f = self.flow()
        f.server_conn = tflow.tserver_conn()
        assert self.q("~b hello | ~b me", f)
        assert self.q("~src :22 | ~b me", f)
        assert not self.q("~src :99 | ~dst :99", f)
        assert self.q("(~src :22 | ~dst :22) | ~b me", f)

    def test_not(self):
        f = self.flow()
        assert not self.q("! ~src :22", f)
        assert self.q("! ~src :99", f)
        assert self.q("!~src :99 !~src :99", f)
        assert not self.q("!~src :99 !~src :22", f)


class TestMatchingDummyFlow:

    def flow(self):
        return tflow.tdummyflow()

    def err(self):
        return tflow.tdummyflow(err=True)

    def q(self, q, o):
        return flowfilter.parse(q)(o)

    def test_filters(self):
        e = self.err()
        f = self.flow()
        f.server_conn = tflow.tserver_conn()

        assert not self.q("~a", f)

        assert not self.q("~b whatever", f)
        assert not self.q("~bq whatever", f)
        assert not self.q("~bs whatever", f)

        assert not self.q("~c 0", f)

        assert not self.q("~d whatever", f)

        assert self.q("~dst address", f)
        assert not self.q("~dst nonexistent", f)

        assert self.q("~e", e)
        assert not self.q("~e", f)

        assert not self.q("~http", f)
        assert not self.q("~tcp", f)
        assert not self.q("~websocket", f)

        assert not self.q("~h whatever", f)
        assert not self.q("~hq whatever", f)
        assert not self.q("~hs whatever", f)

        assert not self.q("~m whatever", f)

        assert not self.q("~s", f)

        assert self.q("~src 127.0.0.1", f)
        assert not self.q("~src nonexistent", f)

        assert not self.q("~tcp", f)

        assert not self.q("~t whatever", f)
        assert not self.q("~tq whatever", f)
        assert not self.q("~ts whatever", f)

        assert not self.q("~u whatever", f)

        assert not self.q("~q", f)

        assert not self.q("~comment .", f)
        f.comment = "comment"
        assert self.q("~comment .", f)


@patch('traceback.extract_tb')
def test_pyparsing_bug(extract_tb):
    """https://github.com/mitmproxy/mitmproxy/issues/1087"""
    # The text is a string with leading and trailing whitespace stripped; if the source is not available it is None.
    extract_tb.return_value = [("", 1, "test", None)]
    assert flowfilter.parse("test")


def test_match():
    with pytest.raises(ValueError):
        flowfilter.match('[foobar', None)

    assert flowfilter.match(None, None)
    assert not flowfilter.match('foobar', None)
