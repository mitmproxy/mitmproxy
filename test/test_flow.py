import Queue, time, os.path
from cStringIO import StringIO
import email.utils
from libmproxy import filt, flow, controller, utils, tnetstring
import tutils


class TestStickyCookieState:
    def _response(self, cookie, host):
        s = flow.StickyCookieState(filt.parse(".*"))
        f = tutils.tflow_full()
        f.request.host = host
        f.response.headers["Set-Cookie"] = [cookie]
        s.handle_response(f)
        return s, f

    def test_domain_match(self):
        s = flow.StickyCookieState(filt.parse(".*"))
        assert s.domain_match("www.google.com", ".google.com")
        assert s.domain_match("google.com", ".google.com")

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


class TestStickyAuthState:
    def test_handle_response(self):
        s = flow.StickyAuthState(filt.parse(".*"))
        f = tutils.tflow_full()
        f.request.headers["authorization"] = ["foo"]
        s.handle_request(f)
        assert "host" in s.hosts

        f = tutils.tflow_full()
        s.handle_request(f)
        assert f.request.headers["authorization"] == ["foo"]


class TestClientPlaybackState:
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


class TestServerPlaybackState:
    def test_hash(self):
        s = flow.ServerPlaybackState(None, [], False, False)
        r = tutils.tflow()
        r2 = tutils.tflow()

        assert s._hash(r)
        assert s._hash(r) == s._hash(r2)
        r.request.headers["foo"] = ["bar"]
        assert s._hash(r) == s._hash(r2)
        r.request.path = "voing"
        assert s._hash(r) != s._hash(r2)

    def test_headers(self):
        s = flow.ServerPlaybackState(["foo"], [], False, False)
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

        s = flow.ServerPlaybackState(None, [r, r2], False, False)
        assert s.count() == 2
        assert len(s.fmap.keys()) == 1

        n = s.next_flow(r)
        assert n.request.headers["key"] == ["one"]
        assert s.count() == 1

        n = s.next_flow(r)
        assert n.request.headers["key"] == ["two"]
        assert s.count() == 0

        assert not s.next_flow(r)

    def test_load_with_nopop(self):
        r = tutils.tflow_full()
        r.request.headers["key"] = ["one"]

        r2 = tutils.tflow_full()
        r2.request.headers["key"] = ["two"]

        s = flow.ServerPlaybackState(None, [r, r2], False, True)

        assert s.count() == 2
        s.next_flow(r)
        assert s.count() == 2


class TestFlow:
    def test_copy(self):
        f = tutils.tflow_full()
        f2 = f.copy()
        assert not f is f2
        assert not f.request is f2.request
        assert f.request.headers == f2.request.headers
        assert not f.request.headers is f2.request.headers
        assert f.response == f2.response
        assert not f.response is f2.response

        f = tutils.tflow_err()
        f2 = f.copy()
        assert not f is f2
        assert not f.request is f2.request
        assert f.request.headers == f2.request.headers
        assert not f.request.headers is f2.request.headers
        assert f.error == f2.error
        assert not f.error is f2.error

    def test_match(self):
        f = tutils.tflow()
        f.response = tutils.tresp()
        f.request = f.response.request
        assert not f.match("~b test")
        assert f.match(None)
        assert not f.match("~b test")

        f = tutils.tflow_err()
        assert f.match("~e")

        tutils.raises(ValueError, f.match, "~")


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

    def test_backup_idempotence(self):
        f = tutils.tflow_full()
        f.backup()
        f.revert()
        f.backup()
        f.revert()

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
        assert not f.request.reply.acked
        f.kill(fm)
        assert f.request.reply.acked
        f.intercept()
        f.response = tutils.tresp()
        f.request = f.response.request
        f.request.reply()
        assert not f.response.reply.acked
        f.kill(fm)
        assert f.response.reply.acked

    def test_killall(self):
        s = flow.State()
        fm = flow.FlowMaster(None, s)

        r = tutils.treq()
        fm.handle_request(r)

        r = tutils.treq()
        fm.handle_request(r)

        for i in s.view:
            assert not i.request.reply.acked
        s.killall(fm)
        for i in s.view:
            assert i.request.reply.acked

    def test_accept_intercept(self):
        f = tutils.tflow()
        f.request = tutils.treq()
        f.intercept()
        assert not f.request.reply.acked
        f.accept_intercept()
        assert f.request.reply.acked
        f.response = tutils.tresp()
        f.request = f.response.request
        f.intercept()
        f.request.reply()
        assert not f.response.reply.acked
        f.accept_intercept()
        assert f.response.reply.acked

    def test_serialization(self):
        f = flow.Flow(None)
        f.request = tutils.treq()

    def test_replace_unicode(self):
        f = tutils.tflow_full()
        f.response.content = "\xc2foo"
        f.replace("foo", u"bar")

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

    def test_replace_encoded(self):
        f = tutils.tflow_full()
        f.request.content = "afoob"
        f.request.encode("gzip")
        f.response.content = "afoob"
        f.response.encode("gzip")

        f.replace("foo", "bar")

        assert f.request.content != "abarb"
        f.request.decode()
        assert f.request.content == "abarb"

        assert f.response.content != "abarb"
        f.response.decode()
        assert f.response.content == "abarb"



class TestState:
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

        c = flow.State()
        req = tutils.treq()
        f = c.add_request(req)
        e = flow.Error(f.request, "message")
        c.set_limit("~e")
        assert not c.view
        assert not c.view
        assert c.add_error(e)
        assert c.view

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


class TestSerialize:
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

    def test_filter(self):
        sio = StringIO()
        fl = filt.parse("~c 200")
        w = flow.FilteredFlowWriter(sio, fl)

        f = tutils.tflow_full()
        f.response.code = 200
        w.add(f)

        f = tutils.tflow_full()
        f.response.code = 201
        w.add(f)

        sio.seek(0)
        r = flow.FlowReader(sio)
        assert len(list(r.stream()))


    def test_error(self):
        sio = StringIO()
        sio.write("bogus")
        sio.seek(0)
        r = flow.FlowReader(sio)
        tutils.raises(flow.FlowReadError, list, r.stream())

        f = flow.FlowReadError("foo")
        assert f.strerror == "foo"

    def test_versioncheck(self):
        f = tutils.tflow()
        d = f._get_state()
        d["version"] = (0, 0)
        sio = StringIO()
        tnetstring.dump(d, sio)
        sio.seek(0)

        r = flow.FlowReader(sio)
        tutils.raises("version", list, r.stream())


class TestFlowMaster:
    def test_load_script(self):
        s = flow.State()
        fm = flow.FlowMaster(None, s)
        assert not fm.load_script(tutils.test_data.path("scripts/a.py"))
        assert not fm.load_script(tutils.test_data.path("scripts/a.py"))
        assert not fm.load_script(None)
        assert fm.load_script("nonexistent")
        assert "ValueError" in fm.load_script(tutils.test_data.path("scripts/starterr.py"))

    def test_replay(self):
        s = flow.State()
        fm = flow.FlowMaster(None, s)
        f = tutils.tflow_full()
        f.request.content = flow.CONTENT_MISSING
        assert "missing" in fm.replay_request(f)

        f.intercepting = True
        assert "intercepting" in fm.replay_request(f)

    def test_script_reqerr(self):
        s = flow.State()
        fm = flow.FlowMaster(None, s)
        assert not fm.load_script(tutils.test_data.path("scripts/reqerr.py"))
        req = tutils.treq()
        fm.handle_clientconnect(req.client_conn)
        assert fm.handle_request(req)

    def test_script(self):
        s = flow.State()
        fm = flow.FlowMaster(None, s)
        assert not fm.load_script(tutils.test_data.path("scripts/all.py"))
        req = tutils.treq()
        fm.handle_clientconnect(req.client_conn)
        assert fm.script.ns["log"][-1] == "clientconnect"
        f = fm.handle_request(req)
        assert fm.script.ns["log"][-1] == "request"
        resp = tutils.tresp(req)
        fm.handle_response(resp)
        assert fm.script.ns["log"][-1] == "response"
        dc = flow.ClientDisconnect(req.client_conn)
        dc.reply = controller.DummyReply()
        fm.handle_clientdisconnect(dc)
        assert fm.script.ns["log"][-1] == "clientdisconnect"
        err = flow.Error(f.request, "msg")
        err.reply = controller.DummyReply()
        fm.handle_error(err)
        assert fm.script.ns["log"][-1] == "error"

    def test_duplicate_flow(self):
        s = flow.State()
        fm = flow.FlowMaster(None, s)
        f = tutils.tflow_full()
        f = fm.load_flow(f)
        assert s.flow_count() == 1
        f2 = fm.duplicate_flow(f)
        assert f2.response
        assert s.flow_count() == 2
        assert s.index(f2)

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
        dc.reply = controller.DummyReply()
        req.client_conn.requestcount = 1
        fm.handle_clientdisconnect(dc)

        err = flow.Error(f.request, "msg")
        err.reply = controller.DummyReply()
        fm.handle_error(err)

        fm.load_script(tutils.test_data.path("scripts/a.py"))
        fm.shutdown()

    def test_client_playback(self):
        s = flow.State()

        f = tutils.tflow_full()
        pb = [tutils.tflow_full(), f]
        fm = flow.FlowMaster(None, s)
        assert not fm.start_server_playback(pb, False, [], False, False)
        assert not fm.start_client_playback(pb, False)

        q = Queue.Queue()
        assert not fm.state.flow_count()
        fm.tick(q)
        assert fm.state.flow_count()

        err = flow.Error(f.request, "error")
        err.reply = controller.DummyReply()
        fm.handle_error(err)

    def test_server_playback(self):
        controller.should_exit = False
        s = flow.State()

        f = tutils.tflow()
        f.response = tutils.tresp(f.request)
        pb = [f]

        fm = flow.FlowMaster(None, s)
        fm.refresh_server_playback = True
        assert not fm.do_server_playback(tutils.tflow())

        fm.start_server_playback(pb, False, [], False, False)
        assert fm.do_server_playback(tutils.tflow())

        fm.start_server_playback(pb, False, [], True, False)
        r = tutils.tflow()
        r.request.content = "gibble"
        assert not fm.do_server_playback(r)
        assert fm.do_server_playback(tutils.tflow())

        fm.start_server_playback(pb, False, [], True, False)
        q = Queue.Queue()
        fm.tick(q)
        assert controller.should_exit

        fm.stop_server_playback()
        assert not fm.server_playback

    def test_server_playback_kill(self):
        s = flow.State()
        f = tutils.tflow()
        f.response = tutils.tresp(f.request)
        pb = [f]
        fm = flow.FlowMaster(None, s)
        fm.refresh_server_playback = True
        fm.start_server_playback(pb, True, [], False, False)

        f = tutils.tflow()
        f.request.host = "nonexistent"
        fm.process_new_request(f)
        assert "killed" in f.error.msg

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
        tf = tf.copy()
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

    def test_stream(self):
        with tutils.tmpdir() as tdir:
            p = os.path.join(tdir, "foo")
            def r():
                r = flow.FlowReader(open(p,"rb"))
                return list(r.stream())

            s = flow.State()
            fm = flow.FlowMaster(None, s)
            tf = tutils.tflow_full()

            fm.start_stream(file(p, "ab"), None)
            fm.handle_request(tf.request)
            fm.handle_response(tf.response)
            fm.stop_stream()

            assert r()[0].response

            tf = tutils.tflow_full()
            fm.start_stream(file(p, "ab"), None)
            fm.handle_request(tf.request)
            fm.shutdown()

            assert not r()[1].response


class TestRequest:
    def test_simple(self):
        h = flow.ODictCaseless()
        h["test"] = ["test"]
        c = flow.ClientConnect(("addr", 2222))
        r = flow.Request(c, (1, 1), "host", 22, "https", "GET", "/", h, "content")
        u = r.get_url()
        assert r.set_url(u)
        assert not r.set_url("")
        assert r.get_url() == u
        assert r._assemble()
        assert r.size() == len(r._assemble())

        r2 = r.copy()
        assert r == r2

        r.content = None
        assert r._assemble()
        assert r.size() == len(r._assemble())

        r.close = True
        assert "connection: close" in r._assemble()

        assert r._assemble(True)

        r.content = flow.CONTENT_MISSING
        assert not r._assemble()

    def test_get_url(self):
        h = flow.ODictCaseless()
        h["test"] = ["test"]
        c = flow.ClientConnect(("addr", 2222))
        r = flow.Request(c, (1, 1), "host", 22, "https", "GET", "/", h, "content")
        assert r.get_url() == "https://host:22/"
        assert r.get_url(hostheader=True) == "https://host:22/"
        r.headers["Host"] = ["foo.com"]
        assert r.get_url() == "https://host:22/"
        assert r.get_url(hostheader=True) == "https://foo.com:22/"

    def test_path_components(self):
        h = flow.ODictCaseless()
        c = flow.ClientConnect(("addr", 2222))
        r = flow.Request(c, (1, 1), "host", 22, "https", "GET", "/", h, "content")
        assert r.get_path_components() == []
        r = flow.Request(c, (1, 1), "host", 22, "https", "GET", "/foo/bar", h, "content")
        assert r.get_path_components() == ["foo", "bar"]
        q = flow.ODict()
        q["test"] = ["123"]
        r.set_query(q)
        assert r.get_path_components() == ["foo", "bar"]

        r.set_path_components([])
        assert r.get_path_components() == []
        r.set_path_components(["foo"])
        assert r.get_path_components() == ["foo"]
        r.set_path_components(["/oo"])
        assert r.get_path_components() == ["/oo"]
        assert "%2F" in r.path

    def test_getset_form_urlencoded(self):
        h = flow.ODictCaseless()
        h["content-type"] = [flow.HDR_FORM_URLENCODED]
        d = flow.ODict([("one", "two"), ("three", "four")])
        r = flow.Request(None, (1, 1), "host", 22, "https", "GET", "/", h, utils.urlencode(d.lst))
        assert r.get_form_urlencoded() == d

        d = flow.ODict([("x", "y")])
        r.set_form_urlencoded(d)
        assert r.get_form_urlencoded() == d

        r.headers["content-type"] = ["foo"]
        assert not r.get_form_urlencoded()

    def test_getset_query(self):
        h = flow.ODictCaseless()

        r = flow.Request(None, (1, 1), "host", 22, "https", "GET", "/foo?x=y&a=b", h, "content")
        q = r.get_query()
        assert q.lst == [("x", "y"), ("a", "b")]

        r = flow.Request(None, (1, 1), "host", 22, "https", "GET", "/", h, "content")
        q = r.get_query()
        assert not q

        r = flow.Request(None, (1, 1), "host", 22, "https", "GET", "/?adsfa", h, "content")
        q = r.get_query()
        assert q.lst == [("adsfa", "")]

        r = flow.Request(None, (1, 1), "host", 22, "https", "GET", "/foo?x=y&a=b", h, "content")
        assert r.get_query()
        r.set_query(flow.ODict([]))
        assert not r.get_query()
        qv = flow.ODict([("a", "b"), ("c", "d")])
        r.set_query(qv)
        assert r.get_query() == qv

    def test_anticache(self):
        h = flow.ODictCaseless()
        r = flow.Request(None, (1, 1), "host", 22, "https", "GET", "/", h, "content")
        h["if-modified-since"] = ["test"]
        h["if-none-match"] = ["test"]
        r.anticache()
        assert not "if-modified-since" in r.headers
        assert not "if-none-match" in r.headers

    def test_getset_state(self):
        h = flow.ODictCaseless()
        h["test"] = ["test"]
        c = flow.ClientConnect(("addr", 2222))
        r = flow.Request(c, (1, 1), "host", 22, "https", "GET", "/", h, "content")
        state = r._get_state()
        assert flow.Request._from_state(state) == r

        r.client_conn = None
        state = r._get_state()
        assert flow.Request._from_state(state) == r

        r2 = flow.Request(c, (1, 1), "testing", 20, "http", "PUT", "/foo", h, "test")
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

    def test_constrain_encoding(self):
        r = tutils.treq()
        r.headers["accept-encoding"] = ["gzip", "oink"]
        r.constrain_encoding()
        assert "oink" not in r.headers["accept-encoding"]

    def test_decodeencode(self):
        r = tutils.treq()
        r.headers["content-encoding"] = ["identity"]
        r.content = "falafel"
        r.decode()
        assert not r.headers["content-encoding"]
        assert r.content == "falafel"

        r = tutils.treq()
        r.content = "falafel"
        assert not r.decode()

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

    def test_get_decoded_content(self):
        r = tutils.treq()
        r.content = None
        r.headers["content-encoding"] = ["identity"]
        assert r.get_decoded_content() == None

        r.content = "falafel"
        r.encode("gzip")
        assert r.get_decoded_content() == "falafel"

    def test_get_cookies_none(self):
        h = flow.ODictCaseless()
        c = flow.ClientConnect(("addr", 2222))
        r = flow.Request(c, (1, 1), "host", 22, "https", "GET", "/", h, "content")
        assert r.get_cookies() == None

    def test_get_cookies_single(self):
        h = flow.ODictCaseless()
        h["Cookie"] = ["cookiename=cookievalue"]
        c = flow.ClientConnect(("addr", 2222))
        r = flow.Request(c, (1, 1), "host", 22, "https", "GET", "/", h, "content")
        result = r.get_cookies()
        assert len(result)==1
        assert result['cookiename']==('cookievalue',{})

    def test_get_cookies_double(self):
        h = flow.ODictCaseless()
        h["Cookie"] = ["cookiename=cookievalue;othercookiename=othercookievalue"]
        c = flow.ClientConnect(("addr", 2222))
        r = flow.Request(c, (1, 1), "host", 22, "https", "GET", "/", h, "content")
        result = r.get_cookies()
        assert len(result)==2
        assert result['cookiename']==('cookievalue',{})
        assert result['othercookiename']==('othercookievalue',{})

    def test_get_cookies_withequalsign(self):
        h = flow.ODictCaseless()
        h["Cookie"] = ["cookiename=coo=kievalue;othercookiename=othercookievalue"]
        c = flow.ClientConnect(("addr", 2222))
        r = flow.Request(c, (1, 1), "host", 22, "https", "GET", "/", h, "content")
        result = r.get_cookies()
        assert len(result)==2
        assert result['cookiename']==('coo=kievalue',{})
        assert result['othercookiename']==('othercookievalue',{})

    def test_get_header_size(self):
        h = flow.ODictCaseless()
        h["headername"] = ["headervalue"]
        c = flow.ClientConnect(("addr", 2222))
        r = flow.Request(c, (1, 1), "host", 22, "https", "GET", "/", h, "content")
        result = r.get_header_size()
        assert result==43

    def test_get_transmitted_size(self):
        h = flow.ODictCaseless()
        h["headername"] = ["headervalue"]
        c = flow.ClientConnect(("addr", 2222))
        r = flow.Request(c, (1, 1), "host", 22, "https", "GET", "/", h, "content")
        result = r.get_transmitted_size()
        assert result==len("content")
        r.content = None
        assert r.get_transmitted_size() == 0

    def test_get_content_type(self):
        h = flow.ODictCaseless()
        h["Content-Type"] = ["text/plain"]
        c = flow.ClientConnect(("addr", 2222))
        r = flow.Request(c, (1, 1), "host", 22, "https", "GET", "/", h, "content")
        assert r.get_content_type()=="text/plain"

class TestResponse:
    def test_simple(self):
        h = flow.ODictCaseless()
        h["test"] = ["test"]
        c = flow.ClientConnect(("addr", 2222))
        req = flow.Request(c, (1, 1), "host", 22, "https", "GET", "/", h, "content")
        resp = flow.Response(req, (1, 1), 200, "msg", h.copy(), "content", None)
        assert resp._assemble()
        assert resp.size() == len(resp._assemble())


        resp2 = resp.copy()
        assert resp2 == resp

        resp.content = None
        assert resp._assemble()
        assert resp.size() == len(resp._assemble())

        resp.content = flow.CONTENT_MISSING
        assert not resp._assemble()

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
        h = flow.ODictCaseless()
        h["test"] = ["test"]
        c = flow.ClientConnect(("addr", 2222))
        req = flow.Request(c, (1, 1), "host", 22, "https", "GET", "/", h, "content")
        resp = flow.Response(req, (1, 1), 200, "msg", h.copy(), "content", None)

        state = resp._get_state()
        assert flow.Response._from_state(req, state) == resp

        resp2 = flow.Response(req, (1, 1), 220, "foo", h.copy(), "test", None)
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

    def test_get_header_size(self):
        r = tutils.tresp()
        result = r.get_header_size()
        assert result==49

    def test_get_cookies_none(self):
        h = flow.ODictCaseless()
        resp = flow.Response(None, (1, 1), 200, "OK", h, "content", None)
        assert not resp.get_cookies()

    def test_get_cookies_simple(self):
        h = flow.ODictCaseless()
        h["Set-Cookie"] = ["cookiename=cookievalue"]
        resp = flow.Response(None, (1, 1), 200, "OK", h, "content", None)
        result = resp.get_cookies()
        assert len(result)==1
        assert "cookiename" in result
        assert result["cookiename"] == ("cookievalue", {})

    def test_get_cookies_with_parameters(self):
        h = flow.ODictCaseless()
        h["Set-Cookie"] = ["cookiename=cookievalue;domain=example.com;expires=Wed Oct  21 16:29:41 2015;path=/; HttpOnly"]
        resp = flow.Response(None, (1, 1), 200, "OK", h, "content", None)
        result = resp.get_cookies()
        assert len(result)==1
        assert "cookiename" in result
        assert result["cookiename"][0] == "cookievalue"
        assert len(result["cookiename"][1])==4
        assert result["cookiename"][1]["domain"]=="example.com"
        assert result["cookiename"][1]["expires"]=="Wed Oct  21 16:29:41 2015"
        assert result["cookiename"][1]["path"]=="/"
        assert result["cookiename"][1]["httponly"]==""

    def test_get_cookies_no_value(self):
        h = flow.ODictCaseless()
        h["Set-Cookie"] = ["cookiename=; Expires=Thu, 01-Jan-1970 00:00:01 GMT; path=/"]
        resp = flow.Response(None, (1, 1), 200, "OK", h, "content", None)
        result = resp.get_cookies()
        assert len(result)==1
        assert "cookiename" in result
        assert result["cookiename"][0] == ""
        assert len(result["cookiename"][1])==2

    def test_get_cookies_twocookies(self):
        h = flow.ODictCaseless()
        h["Set-Cookie"] = ["cookiename=cookievalue","othercookie=othervalue"]
        resp = flow.Response(None, (1, 1), 200, "OK", h, "content", None)
        result = resp.get_cookies()
        assert len(result)==2
        assert "cookiename" in result
        assert result["cookiename"] == ("cookievalue", {})
        assert "othercookie" in result
        assert result["othercookie"] == ("othervalue", {})

    def test_get_content_type(self):
        h = flow.ODictCaseless()
        h["Content-Type"] = ["text/plain"]
        resp = flow.Response(None, (1, 1), 200, "OK", h, "content", None)
        assert resp.get_content_type()=="text/plain"


class TestError:
    def test_getset_state(self):
        e = flow.Error(None, "Error")
        state = e._get_state()
        assert flow.Error._from_state(None, state) == e

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


class TestClientConnect:
    def test_state(self):
        c = flow.ClientConnect(("a", 22))
        assert flow.ClientConnect._from_state(c._get_state()) == c

        c2 = flow.ClientConnect(("a", 25))
        assert not c == c2

        c2.requestcount = 99
        c._load_state(c2._get_state())
        assert c.requestcount == 99

        c3 = c.copy()
        assert c3 == c

        assert str(c)


def test_decoded():
    r = tutils.treq()
    assert r.content == "content"
    assert not r.headers["content-encoding"]
    r.encode("gzip")
    assert r.headers["content-encoding"]
    assert r.content != "content"
    with flow.decoded(r):
        assert not r.headers["content-encoding"]
        assert r.content == "content"
    assert r.headers["content-encoding"]
    assert r.content != "content"

    with flow.decoded(r):
        r.content = "foo"

    assert r.content != "foo"
    r.decode()
    assert r.content == "foo"


def test_replacehooks():
    h = flow.ReplaceHooks()
    h.add("~q", "foo", "bar")
    assert h.lst

    h.set(
        [
            (".*", "one", "two"),
            (".*", "three", "four"),
        ]
    )
    assert h.count() == 2

    h.clear()
    assert not h.lst

    h.add("~q", "foo", "bar")
    h.add("~s", "foo", "bar")

    v = h.get_specs()
    assert v == [('~q', 'foo', 'bar'), ('~s', 'foo', 'bar')]
    assert h.count() == 2
    h.clear()
    assert h.count() == 0

    f = tutils.tflow()
    f.request.content = "foo"
    h.add("~s", "foo", "bar")
    h.run(f)
    assert f.request.content == "foo"

    f = tutils.tflow_full()
    f.request.content = "foo"
    f.response.content = "foo"
    h.run(f)
    assert f.response.content == "bar"
    assert f.request.content == "foo"

    f = tutils.tflow()
    h.clear()
    h.add("~q", "foo", "bar")
    f.request.content = "foo"
    h.run(f)
    assert f.request.content == "bar"

    assert not h.add("~", "foo", "bar")
    assert not h.add("foo", "*", "bar")


def test_setheaders():
    h = flow.SetHeaders()
    h.add("~q", "foo", "bar")
    assert h.lst

    h.set(
        [
            (".*", "one", "two"),
            (".*", "three", "four"),
        ]
    )
    assert h.count() == 2

    h.clear()
    assert not h.lst

    h.add("~q", "foo", "bar")
    h.add("~s", "foo", "bar")

    v = h.get_specs()
    assert v == [('~q', 'foo', 'bar'), ('~s', 'foo', 'bar')]
    assert h.count() == 2
    h.clear()
    assert h.count() == 0

    f = tutils.tflow()
    f.request.content = "foo"
    h.add("~s", "foo", "bar")
    h.run(f)
    assert f.request.content == "foo"


    h.clear()
    h.add("~s", "one", "two")
    h.add("~s", "one", "three")
    f = tutils.tflow_full()
    f.request.headers["one"] = ["xxx"]
    f.response.headers["one"] = ["xxx"]
    h.run(f)
    assert f.request.headers["one"] == ["xxx"]
    assert f.response.headers["one"] == ["two", "three"]

    h.clear()
    h.add("~q", "one", "two")
    h.add("~q", "one", "three")
    f = tutils.tflow()
    f.request.headers["one"] = ["xxx"]
    h.run(f)
    assert f.request.headers["one"] == ["two", "three"]

    assert not h.add("~", "foo", "bar")
