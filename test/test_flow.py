import Queue, time, textwrap
from cStringIO import StringIO
import email.utils
from libmproxy import console, proxy, filt, flow, controller, utils
import tutils
import libpry


class uStickyCookieState(libpry.AutoTree):
    def _response(self, cookie, host):
        s = flow.StickyCookieState(filt.parse(".*"))
        f = tutils.tflow_full()
        f.request.host = host 
        f.response.headers["Set-Cookie"] = [cookie]
        s.handle_response(f)
        return s, f

    def test_handle_response(self):
        c = "SSID=mooo, FOO=bar; Domain=.google.com; Path=/; "\
            "Expires=Wed, 13-Jan-2021 22:23:01 GMT; Secure; "

        s, f = self._response(c, "host")
        assert not s.jar.keys()

        s, f = self._response(c, "www.google.com")
        assert s.jar.keys()

        s, f = self._response("SSID=mooo", "www.google.com")
        assert s.jar.keys()[0] == ('www.google.com', 80, '/')

    def test_handle_request(self):
        s, f = self._response("SSID=mooo", "www.google.com")
        assert "cookie" not in f.request.headers
        s.handle_request(f)
        assert "cookie" in f.request.headers


class uStickyAuthState(libpry.AutoTree):
    def test_handle_response(self):
        s = flow.StickyAuthState(filt.parse(".*"))
        f = tutils.tflow_full()
        f.request.headers["authorization"] = ["foo"]
        s.handle_request(f)
        assert "host" in s.hosts

        f = tutils.tflow_full()
        s.handle_request(f)
        assert f.request.headers["authorization"] == ["foo"]


class uClientPlaybackState(libpry.AutoTree):
    def test_tick(self):
        first = tutils.tflow()
        s = flow.State()
        fm = flow.FlowMaster(None, s)
        fm.start_client_playback([first, tutils.tflow()], True)
        c = fm.client_playback

        assert not c.done()
        assert not s.flow_count()
        assert c.count() == 2
        c.tick(fm, testing=True)
        assert s.flow_count()
        assert c.count() == 1

        c.tick(fm, testing=True)
        assert c.count() == 1

        c.clear(c.current)
        c.tick(fm, testing=True)
        assert c.count() == 0
        c.clear(c.current)
        assert c.done()

        q = Queue.Queue()
        fm.state.clear()
        fm.tick(q)

        fm.stop_client_playback()
        assert not fm.client_playback


class uServerPlaybackState(libpry.AutoTree):
    def test_hash(self):
        s = flow.ServerPlaybackState(None, [], False)
        r = tutils.tflow()
        r2 = tutils.tflow()

        assert s._hash(r)
        assert s._hash(r) == s._hash(r2)
        r.request.headers["foo"] = ["bar"]
        assert s._hash(r) == s._hash(r2)
        r.request.path = "voing"
        assert s._hash(r) != s._hash(r2)

    def test_headers(self):
        s = flow.ServerPlaybackState(["foo"], [], False)
        r = tutils.tflow_full()
        r.request.headers["foo"] = ["bar"]
        r2 = tutils.tflow_full()
        assert not s._hash(r) == s._hash(r2)
        r2.request.headers["foo"] = ["bar"]
        assert s._hash(r) == s._hash(r2)
        r2.request.headers["oink"] = ["bar"]
        assert s._hash(r) == s._hash(r2)

        r = tutils.tflow_full()
        r2 = tutils.tflow_full()
        assert s._hash(r) == s._hash(r2)

    def test_load(self):
        r = tutils.tflow_full()
        r.request.headers["key"] = ["one"]

        r2 = tutils.tflow_full()
        r2.request.headers["key"] = ["two"]

        s = flow.ServerPlaybackState(None, [r, r2], False)
        assert s.count() == 2
        assert len(s.fmap.keys()) == 1

        n = s.next_flow(r)
        assert n.request.headers["key"] == ["one"]
        assert s.count() == 1

        n = s.next_flow(r)
        assert n.request.headers["key"] == ["two"]
        assert s.count() == 0

        assert not s.next_flow(r)


class uFlow(libpry.AutoTree):
    def test_match(self):
        f = tutils.tflow()
        f.response = tutils.tresp()
        f.request = f.response.request
        assert not f.match(filt.parse("~b test"))
        assert f.match(None)

    def test_backup(self):
        f = tutils.tflow()
        f.response = tutils.tresp()
        f.request = f.response.request
        f.request.content = "foo"
        assert not f.modified()
        f.backup()
        f.request.content = "bar"
        assert f.modified()
        f.revert()
        assert f.request.content == "foo"

    def test_getset_state(self):
        f = tutils.tflow()
        f.response = tutils.tresp(f.request)
        state = f._get_state() 
        assert f._get_state() == flow.Flow._from_state(state)._get_state()

        f.response = None
        f.error = flow.Error(f.request, "error")
        state = f._get_state() 
        assert f._get_state() == flow.Flow._from_state(state)._get_state()

        f2 = tutils.tflow()
        f2.error = flow.Error(f.request, "e2")
        assert not f == f2
        f._load_state(f2._get_state())
        assert f._get_state() == f2._get_state()

    def test_kill(self):
        s = flow.State()
        fm = flow.FlowMaster(None, s)
        f = tutils.tflow()
        f.request = tutils.treq()
        f.intercept()
        assert not f.request.acked
        f.kill(fm)
        assert f.request.acked
        f.intercept()
        f.response = tutils.tresp()
        f.request = f.response.request
        f.request._ack()
        assert not f.response.acked
        f.kill(fm)
        assert f.response.acked

    def test_killall(self):
        s = flow.State()
        fm = flow.FlowMaster(None, s)

        r = tutils.treq()
        fm.handle_request(r)

        r = tutils.treq()
        fm.handle_request(r)

        for i in s.view:
            assert not i.request.acked
        s.killall(fm)
        for i in s.view:
            assert i.request.acked

    def test_accept_intercept(self):
        f = tutils.tflow()
        f.request = tutils.treq()
        f.intercept()
        assert not f.request.acked
        f.accept_intercept()
        assert f.request.acked
        f.response = tutils.tresp()
        f.request = f.response.request
        f.intercept()
        f.request._ack()
        assert not f.response.acked
        f.accept_intercept()
        assert f.response.acked

    def test_serialization(self):
        f = flow.Flow(None)
        f.request = tutils.treq()

    def test_replace(self):
        f = tutils.tflow_full()
        f.request.headers["foo"] = ["foo"]
        f.request.content = "afoob"

        f.response.headers["foo"] = ["foo"]
        f.response.content = "afoob"

        assert f.replace("foo", "bar") == 6

        assert f.request.headers["bar"] == ["bar"]
        assert f.request.content == "abarb"
        assert f.response.headers["bar"] == ["bar"]
        assert f.response.content == "abarb"

        f = tutils.tflow_err()
        f.replace("error", "bar")
        assert f.error.msg == "bar"


class uState(libpry.AutoTree):
    def test_backup(self):
        c = flow.State()
        req = tutils.treq()
        f = c.add_request(req)

        f.backup()
        c.revert(f)

    def test_flow(self):
        """
            normal flow:

                connect -> request -> response
        """
        bc = flow.ClientConnect(("address", 22))
        c = flow.State()

        req = tutils.treq(bc)
        f = c.add_request(req)
        assert f
        assert c.flow_count() == 1
        assert c._flow_map.get(req)
        assert c.active_flow_count() == 1

        newreq = tutils.treq()
        assert c.add_request(newreq)
        assert c._flow_map.get(newreq)
        assert c.active_flow_count() == 2

        resp = tutils.tresp(req)
        assert c.add_response(resp)
        assert c.flow_count() == 2
        assert c._flow_map.get(resp.request)
        assert c.active_flow_count() == 1

        unseen_resp = tutils.tresp()
        assert not c.add_response(unseen_resp)
        assert not c._flow_map.get(unseen_resp.request)
        assert c.active_flow_count() == 1

        resp = tutils.tresp(newreq)
        assert c.add_response(resp)
        assert c.active_flow_count() == 0


    def test_err(self):
        c = flow.State()
        req = tutils.treq()
        f = c.add_request(req)
        e = flow.Error(f.request, "message")
        assert c.add_error(e)

        e = flow.Error(tutils.tflow().request, "message")
        assert not c.add_error(e)


    def test_set_limit(self):
        c = flow.State()

        req = tutils.treq()
        assert len(c.view) == 0

        c.add_request(req)
        assert len(c.view) == 1

        c.set_limit("~s")
        assert c.limit_txt == "~s"
        assert len(c.view) == 0
        resp = tutils.tresp(req)
        c.add_response(resp)
        assert len(c.view) == 1
        c.set_limit(None)
        assert len(c.view) == 1

        req = tutils.treq()
        c.add_request(req)
        assert len(c.view) == 2
        c.set_limit("~q")
        assert len(c.view) == 1
        c.set_limit("~s")
        assert len(c.view) == 1

        assert "Invalid" in c.set_limit("~")

    def test_set_intercept(self):
        c = flow.State()
        assert not c.set_intercept("~q")
        assert c.intercept_txt == "~q"
        assert "Invalid" in c.set_intercept("~")
        assert not c.set_intercept(None)
        assert c.intercept_txt == None

    def _add_request(self, state):
        req = tutils.treq()
        f = state.add_request(req)
        return f

    def _add_response(self, state):
        req = tutils.treq()
        state.add_request(req)
        resp = tutils.tresp(req)
        state.add_response(resp)

    def _add_error(self, state):
        req = tutils.treq()
        f = state.add_request(req)
        f.error = flow.Error(f.request, "msg")

    def test_clear(self):
        c = flow.State()
        f = self._add_request(c)
        f.intercepting = True

        c.clear()
        assert c.flow_count() == 0

    def test_dump_flows(self):
        c = flow.State()
        self._add_request(c)
        self._add_response(c)
        self._add_request(c)
        self._add_response(c)
        self._add_request(c)
        self._add_response(c)
        self._add_error(c)

        flows = c.view[:]
        c.clear()
        
        c.load_flows(flows)
        assert isinstance(c._flow_list[0], flow.Flow)

    def test_accept_all(self):
        c = flow.State()
        self._add_request(c)
        self._add_response(c)
        self._add_request(c)
        c.accept_all()


class uSerialize(libpry.AutoTree):
    def _treader(self):
        sio = StringIO()
        w = flow.FlowWriter(sio)
        for i in range(3):
            f = tutils.tflow_full()
            w.add(f)
        for i in range(3):
            f = tutils.tflow_err()
            w.add(f)

        sio.seek(0)
        return flow.FlowReader(sio)

    def test_roundtrip(self):
        sio = StringIO()
        f = tutils.tflow()
        f.request.content = "".join(chr(i) for i in range(255))
        w = flow.FlowWriter(sio)
        w.add(f)

        sio.seek(0)
        r = flow.FlowReader(sio)
        l = list(r.stream())
        assert len(l) == 1

        f2 = l[0]
        assert f2._get_state() == f._get_state()
        assert f2.request._assemble() == f.request._assemble()

    def test_load_flows(self):
        r = self._treader()
        s = flow.State()
        fm = flow.FlowMaster(None, s)
        fm.load_flows(r)
        assert len(s._flow_list) == 6


    def test_error(self):
        sio = StringIO()
        sio.write("bogus")
        sio.seek(0)
        r = flow.FlowReader(sio)
        libpry.raises(flow.FlowReadError, list, r.stream())

        f = flow.FlowReadError("foo")
        assert f.strerror == "foo"


class uFlowMaster(libpry.AutoTree):
    def test_load_script(self):
        s = flow.State()
        fm = flow.FlowMaster(None, s)
        assert not fm.load_script("scripts/a.py")
        assert fm.load_script("nonexistent")
        assert "ValueError" in fm.load_script("scripts/starterr.py")

    def test_script(self):
        s = flow.State()
        fm = flow.FlowMaster(None, s)
        assert not fm.load_script("scripts/all.py")
        req = tutils.treq()
        fm.handle_clientconnect(req.client_conn)
        assert fm.script.ns["log"][-1] == "clientconnect"
        f = fm.handle_request(req)
        assert fm.script.ns["log"][-1] == "request"
        resp = tutils.tresp(req)
        fm.handle_response(resp)
        assert fm.script.ns["log"][-1] == "response"
        dc = flow.ClientDisconnect(req.client_conn)
        fm.handle_clientdisconnect(dc)
        assert fm.script.ns["log"][-1] == "clientdisconnect"
        err = flow.Error(f.request, "msg")
        fm.handle_error(err)
        assert fm.script.ns["log"][-1] == "error"

    def test_all(self):
        s = flow.State()
        fm = flow.FlowMaster(None, s)
        fm.anticache = True
        fm.anticomp = True
        req = tutils.treq()
        fm.handle_clientconnect(req.client_conn)

        f = fm.handle_request(req)
        assert s.flow_count() == 1

        resp = tutils.tresp(req)
        fm.handle_response(resp)
        assert s.flow_count() == 1

        rx = tutils.tresp()
        assert not fm.handle_response(rx)
        
        dc = flow.ClientDisconnect(req.client_conn)
        fm.handle_clientdisconnect(dc)

        err = flow.Error(f.request, "msg")
        fm.handle_error(err)

    def test_client_playback(self):
        s = flow.State()

        f = tutils.tflow_full()
        pb = [tutils.tflow_full(), f]
        fm = flow.FlowMaster(None, s)
        assert not fm.start_server_playback(pb, False, [], False)
        assert not fm.start_client_playback(pb, False)

        q = Queue.Queue()
        assert not fm.state.flow_count()
        fm.tick(q)
        assert fm.state.flow_count()

        fm.handle_error(flow.Error(f.request, "error"))

    def test_server_playback(self):
        s = flow.State()

        f = tutils.tflow()
        f.response = tutils.tresp(f.request)
        pb = [f]

        fm = flow.FlowMaster(None, s)
        fm.refresh_server_playback = True
        assert not fm.do_server_playback(tutils.tflow())

        fm.start_server_playback(pb, False, [], False)
        assert fm.do_server_playback(tutils.tflow())

        fm.start_server_playback(pb, False, [], True)
        r = tutils.tflow()
        r.request.content = "gibble"
        assert not fm.do_server_playback(r)

        assert fm.do_server_playback(tutils.tflow())
        q = Queue.Queue()
        fm.tick(q)
        assert controller.should_exit

        fm.stop_server_playback()
        assert not fm.server_playback

    def test_stickycookie(self):
        s = flow.State()
        fm = flow.FlowMaster(None, s)
        assert "Invalid" in fm.set_stickycookie("~h")
        fm.set_stickycookie(".*")
        assert fm.stickycookie_state
        fm.set_stickycookie(None)
        assert not fm.stickycookie_state

        fm.set_stickycookie(".*")
        tf = tutils.tflow_full()
        tf.response.headers["set-cookie"] = ["foo=bar"]
        fm.handle_request(tf.request)
        fm.handle_response(tf.response)
        assert fm.stickycookie_state.jar
        assert not "cookie" in tf.request.headers
        fm.handle_request(tf.request)
        assert tf.request.headers["cookie"] == ["foo=bar"]

    def test_stickyauth(self):
        s = flow.State()
        fm = flow.FlowMaster(None, s)
        assert "Invalid" in fm.set_stickyauth("~h")
        fm.set_stickyauth(".*")
        assert fm.stickyauth_state
        fm.set_stickyauth(None)
        assert not fm.stickyauth_state

        fm.set_stickyauth(".*")
        tf = tutils.tflow_full()
        tf.request.headers["authorization"] = ["foo"]
        fm.handle_request(tf.request)

        f = tutils.tflow_full()
        assert fm.stickyauth_state.hosts
        assert not "authorization" in f.request.headers
        fm.handle_request(f.request)
        assert f.request.headers["authorization"] == ["foo"]

class uRequest(libpry.AutoTree):
    def test_simple(self):
        h = flow.Headers()
        h["test"] = ["test"]
        c = flow.ClientConnect(("addr", 2222))
        r = flow.Request(c, "host", 22, "https", "GET", "/", h, "content")
        u = r.get_url()
        assert r.set_url(u)
        assert not r.set_url("")
        assert r.get_url() == u
        assert r._assemble()

        r2 = r.copy()
        assert r == r2

    def test_anticache(self):
        h = flow.Headers()
        r = flow.Request(None, "host", 22, "https", "GET", "/", h, "content")
        h["if-modified-since"] = ["test"]
        h["if-none-match"] = ["test"]
        r.anticache()
        assert not "if-modified-since" in r.headers
        assert not "if-none-match" in r.headers

    def test_getset_state(self):
        h = flow.Headers()
        h["test"] = ["test"]
        c = flow.ClientConnect(("addr", 2222))
        r = flow.Request(c, "host", 22, "https", "GET", "/", h, "content")
        state = r._get_state()
        assert flow.Request._from_state(state) == r

        r.client_conn = None
        state = r._get_state()
        assert flow.Request._from_state(state) == r

        r2 = flow.Request(c, "testing", 20, "http", "PUT", "/foo", h, "test")
        assert not r == r2
        r._load_state(r2._get_state())
        assert r == r2

        r2.client_conn = None
        r._load_state(r2._get_state())
        assert not r.client_conn

    def test_replace(self):
        r = tutils.treq()
        r.path = "path/foo"
        r.headers["Foo"] = ["fOo"]
        r.content = "afoob"
        assert r.replace("foo(?i)", "boo") == 4
        assert r.path == "path/boo"
        assert not "foo" in r.content
        assert r.headers["boo"] == ["boo"]

    def test_decodeencode(self):
        r = tutils.treq()
        r.headers["content-encoding"] = ["identity"]
        r.content = "falafel"
        r.decode()
        assert not r.headers["content-encoding"]
        assert r.content == "falafel"

        r = tutils.treq()
        r.headers["content-encoding"] = ["identity"]
        r.content = "falafel"
        r.encode("identity")
        assert r.headers["content-encoding"] == ["identity"]
        assert r.content == "falafel"

        r = tutils.treq()
        r.headers["content-encoding"] = ["identity"]
        r.content = "falafel"
        r.encode("gzip")
        assert r.headers["content-encoding"] == ["gzip"]
        assert r.content != "falafel"
        r.decode()
        assert not r.headers["content-encoding"]
        assert r.content == "falafel"


class uResponse(libpry.AutoTree):
    def test_simple(self):
        h = flow.Headers()
        h["test"] = ["test"]
        c = flow.ClientConnect(("addr", 2222))
        req = flow.Request(c, "host", 22, "https", "GET", "/", h, "content")
        resp = flow.Response(req, 200, "msg", h.copy(), "content")
        assert resp._assemble()

        resp2 = resp.copy()
        assert resp2 == resp

    def test_refresh(self):
        r = tutils.tresp()
        n = time.time()
        r.headers["date"] = [email.utils.formatdate(n)]
        pre = r.headers["date"]
        r.refresh(n)
        assert pre == r.headers["date"]
        r.refresh(n+60)

        d = email.utils.parsedate_tz(r.headers["date"][0])
        d = email.utils.mktime_tz(d)
        # Weird that this is not exact...
        assert abs(60-(d-n)) <= 1

        r.headers["set-cookie"] = ["MOO=BAR; Expires=Tue, 08-Mar-2011 00:20:38 GMT; Path=foo.com; Secure"]
        r.refresh()

    def test_refresh_cookie(self):
        r = tutils.tresp()

        # Invalid expires format, sent to us by Reddit.
        c = "rfoo=bar; Domain=reddit.com; expires=Thu, 31 Dec 2037 23:59:59 GMT; Path=/"
        assert r._refresh_cookie(c, 60)

        c = "MOO=BAR; Expires=Tue, 08-Mar-2011 00:20:38 GMT; Path=foo.com; Secure"
        assert "00:21:38" in r._refresh_cookie(c, 60)


    def test_getset_state(self):
        h = flow.Headers()
        h["test"] = ["test"]
        c = flow.ClientConnect(("addr", 2222))
        req = flow.Request(c, "host", 22, "https", "GET", "/", h, "content")
        resp = flow.Response(req, 200, "msg", h.copy(), "content")

        state = resp._get_state()
        assert flow.Response._from_state(req, state) == resp

        resp2 = flow.Response(req, 220, "foo", h.copy(), "test")
        assert not resp == resp2
        resp._load_state(resp2._get_state())
        assert resp == resp2

    def test_replace(self):
        r = tutils.tresp()
        r.headers["Foo"] = ["fOo"]
        r.content = "afoob"
        assert r.replace("foo(?i)", "boo") == 3
        assert not "foo" in r.content
        assert r.headers["boo"] == ["boo"]

    def test_decodeencode(self):
        r = tutils.tresp()
        r.headers["content-encoding"] = ["identity"]
        r.content = "falafel"
        r.decode()
        assert not r.headers["content-encoding"]
        assert r.content == "falafel"

        r = tutils.tresp()
        r.headers["content-encoding"] = ["identity"]
        r.content = "falafel"
        r.encode("identity")
        assert r.headers["content-encoding"] == ["identity"]
        assert r.content == "falafel"

        r = tutils.tresp()
        r.headers["content-encoding"] = ["identity"]
        r.content = "falafel"
        r.encode("gzip")
        assert r.headers["content-encoding"] == ["gzip"]
        assert r.content != "falafel"
        r.decode()
        assert not r.headers["content-encoding"]
        assert r.content == "falafel"


class uError(libpry.AutoTree):
    def test_getset_state(self):
        e = flow.Error(None, "Error")
        state = e._get_state()
        assert flow.Error._from_state(state) == e

        assert e.copy()

        e2 = flow.Error(None, "bar")
        assert not e == e2
        e._load_state(e2._get_state())
        assert e == e2


        e3 = e.copy()
        assert e3 == e

    def test_replace(self):
        e = flow.Error(None, "amoop")
        e.replace("moo", "bar")
        assert e.msg == "abarp"


class uClientConnect(libpry.AutoTree):
    def test_state(self):
        c = flow.ClientConnect(("a", 22))
        assert flow.ClientConnect._from_state(c._get_state()) == c

        c2 = flow.ClientConnect(("a", 25))
        assert not c == c2

        c._load_state(c2._get_state())
        assert c == c2

        c3 = c.copy()
        assert c3 == c


class uHeaders(libpry.AutoTree):
    def setUp(self):
        self.hd = flow.Headers()

    def test_read_simple(self):
        data = """
            Header: one
            Header2: two
            \r\n
        """
        data = textwrap.dedent(data)
        data = data.strip()
        s = StringIO(data)
        self.hd.read(s)
        assert self.hd["header"] == ["one"]
        assert self.hd["header2"] == ["two"]

    def test_read_multi(self):
        data = """
            Header: one
            Header: two
            \r\n
        """
        data = textwrap.dedent(data)
        data = data.strip()
        s = StringIO(data)
        self.hd.read(s)
        assert self.hd["header"] == ["one", "two"]

    def test_read_continued(self):
        data = """
            Header: one
            \ttwo
            Header2: three
            \r\n
        """
        data = textwrap.dedent(data)
        data = data.strip()
        s = StringIO(data)
        self.hd.read(s)
        assert self.hd["header"] == ['one\r\n two']

    def test_dictToHeader1(self):
        self.hd.add("one", "uno")
        self.hd.add("two", "due")
        self.hd.add("two", "tre")
        expected = [
            "one: uno\r\n",
            "two: due\r\n",
            "two: tre\r\n",
            "\r\n"
        ]
        out = repr(self.hd)
        for i in expected:
            assert out.find(i) >= 0

    def test_dictToHeader2(self):
        self.hd["one"] = ["uno"]
        expected1 = "one: uno\r\n"
        expected2 = "\r\n"
        out = repr(self.hd)
        assert out.find(expected1) >= 0
        assert out.find(expected2) >= 0

    def test_match_re(self):
        h = flow.Headers()
        h.add("one", "uno")
        h.add("two", "due")
        h.add("two", "tre")
        assert h.match_re("uno")
        assert h.match_re("two: due")
        assert not h.match_re("nonono")

    def test_getset_state(self):
        self.hd.add("foo", 1)
        self.hd.add("foo", 2)
        self.hd.add("bar", 3)
        state = self.hd._get_state()
        nd = flow.Headers._from_state(state)
        assert nd == self.hd

    def test_copy(self):
        self.hd.add("foo", 1)
        self.hd.add("foo", 2)
        self.hd.add("bar", 3)
        assert self.hd == self.hd.copy()

    def test_del(self):
        self.hd.add("foo", 1)
        self.hd.add("Foo", 2)
        self.hd.add("bar", 3)
        del self.hd["foo"]
        assert len(self.hd.lst) == 1

    def test_replace(self):
        self.hd.add("one", "two")
        self.hd.add("two", "one")
        assert self.hd.replace("one", "vun") == 2
        assert self.hd.lst == [
            ["vun", "two"],
            ["two", "vun"],
        ]


tests = [
    uStickyCookieState(),
    uStickyAuthState(),
    uServerPlaybackState(),
    uClientPlaybackState(),
    uFlow(),
    uState(),
    uSerialize(),
    uFlowMaster(),
    uRequest(),
    uResponse(),
    uError(),
    uClientConnect(),
    uHeaders(),
]
