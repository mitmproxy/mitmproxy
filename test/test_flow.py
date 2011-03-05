from cStringIO import StringIO
from libmproxy import console, proxy, filt, flow
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


class uClientPlaybackState(libpry.AutoTree):
    def test_tick(self):
        first = tutils.tflow()
        c = flow.ClientPlaybackState(
            [first, tutils.tflow()]
        )
        s = flow.State()
        fm = flow.FlowMaster(None, s)
        assert not s.flow_map
        assert c.count() == 2
        c.tick(fm, testing=True)
        assert s.flow_map
        assert c.count() == 1

        c.tick(fm, testing=True)
        assert c.count() == 1

        c.clear(first)
        c.tick(fm, testing=True)
        assert c.count() == 0



class uServerPlaybackState(libpry.AutoTree):
    def test_hash(self):
        s = flow.ServerPlaybackState(None, [])
        r = tutils.tflow()
        r2 = tutils.tflow()

        assert s._hash(r)
        assert s._hash(r) == s._hash(r2)
        r.request.headers["foo"] = ["bar"]
        assert s._hash(r) == s._hash(r2)
        r.request.path = "voing"
        assert s._hash(r) != s._hash(r2)

    def test_headers(self):
        s = flow.ServerPlaybackState(["foo"], [])
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

        s = flow.ServerPlaybackState(None, [r, r2])
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
    def test_run_script(self):
        f = tutils.tflow()
        f.response = tutils.tresp()
        f.request = f.response.request
        se = f.run_script("scripts/a")
        assert "DEBUG" == se.strip()
        assert f.request.host == "TESTOK"

    def test_run_script_err(self):
        f = tutils.tflow()
        f.response = tutils.tresp()
        f.request = f.response.request
        libpry.raises("returned error", f.run_script,"scripts/err_return")
        libpry.raises("invalid response", f.run_script,"scripts/err_data")
        libpry.raises("no such file", f.run_script,"nonexistent")
        libpry.raises("permission denied", f.run_script,"scripts/nonexecutable")

    def test_match(self):
        f = tutils.tflow()
        f.response = tutils.tresp()
        f.request = f.response.request
        assert not f.match(filt.parse("~b test"))
        assert not f.match(None)

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
        state = f.get_state() 
        assert f == flow.Flow.from_state(state)

        f.response = None
        f.error = proxy.Error(f.request, "error")
        state = f.get_state() 
        assert f == flow.Flow.from_state(state)

        f2 = tutils.tflow()
        f2.error = proxy.Error(f.request, "e2")
        assert not f == f2
        f.load_state(f2.get_state())
        assert f == f2



    def test_kill(self):
        f = tutils.tflow()
        f.request = tutils.treq()
        f.intercept()
        assert not f.request.acked
        f.kill()
        assert f.request.acked
        f.intercept()
        f.response = tutils.tresp()
        f.request = f.response.request
        f.request.ack()
        assert not f.response.acked
        f.kill()
        assert f.response.acked

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
        f.request.ack()
        assert not f.response.acked
        f.accept_intercept()
        assert f.response.acked

    def test_serialization(self):
        f = flow.Flow(None)
        f.request = tutils.treq()


class uState(libpry.AutoTree):
    def test_backup(self):
        bc = proxy.ClientConnect(("address", 22))
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
        bc = proxy.ClientConnect(("address", 22))
        c = flow.State()
        c.clientconnect(bc)
        assert len(c.client_connections) == 1

        req = tutils.treq(bc)
        f = c.add_request(req)
        assert f
        assert len(c.flow_list) == 1
        assert c.flow_map.get(req)

        newreq = tutils.treq()
        assert c.add_request(newreq)
        assert c.flow_map.get(newreq)

        resp = tutils.tresp(req)
        assert c.add_response(resp)
        assert len(c.flow_list) == 2
        assert c.flow_map.get(resp.request)

        newresp = tutils.tresp()
        assert not c.add_response(newresp)
        assert not c.flow_map.get(newresp.request)

        dc = proxy.ClientDisconnect(bc)
        c.clientdisconnect(dc)
        assert not c.client_connections

    def test_err(self):
        bc = proxy.ClientConnect(("address", 22))
        c = flow.State()
        req = tutils.treq()
        f = c.add_request(req)
        e = proxy.Error(f.request, "message")
        assert c.add_error(e)

        e = proxy.Error(tutils.tflow().request, "message")
        assert not c.add_error(e)

    def test_view(self):
        c = flow.State()

        req = tutils.treq()
        c.clientconnect(req.client_conn)
        assert len(c.view) == 0

        f = c.add_request(req)
        assert len(c.view) == 1

        c.set_limit(filt.parse("~s"))
        assert len(c.view) == 0
        resp = tutils.tresp(req)
        c.add_response(resp)
        assert len(c.view) == 1
        c.set_limit(None)
        assert len(c.view) == 1

        req = tutils.treq()
        c.clientconnect(req.client_conn)
        c.add_request(req)
        assert len(c.view) == 2
        c.set_limit(filt.parse("~q"))
        assert len(c.view) == 1
        c.set_limit(filt.parse("~s"))
        assert len(c.view) == 1

    def _add_request(self, state):
        req = tutils.treq()
        f = state.add_request(req)
        return f

    def _add_response(self, state):
        req = tutils.treq()
        f = state.add_request(req)
        resp = tutils.tresp(req)
        state.add_response(resp)

    def _add_error(self, state):
        req = tutils.treq()
        f = state.add_request(req)
        f.error = proxy.Error(f.request, "msg")

    def test_kill_flow(self):
        c = flow.State()
        req = tutils.treq()
        f = c.add_request(req)
        c.kill_flow(f)
        assert not c.flow_list

    def test_clear(self):
        c = flow.State()
        f = self._add_request(c)
        f.intercepting = True

        c.clear()
        assert len(c.flow_list) == 1
        f.intercepting = False
        c.clear()
        assert len(c.flow_list) == 0

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
        assert isinstance(c.flow_list[0], flow.Flow)

    def test_accept_all(self):
        c = flow.State()
        self._add_request(c)
        self._add_response(c)
        self._add_request(c)
        c.accept_all()


class uSerialize(libpry.AutoTree):
    def test_roundtrip(self):
        sio = StringIO()
        f = tutils.tflow()
        w = flow.FlowWriter(sio)
        w.add(f)

        sio.seek(0)
        r = flow.FlowReader(sio)
        l = list(r.stream())
        assert len(l) == 1
        assert l[0] == f


class uFlowMaster(libpry.AutoTree):
    def test_all(self):
        s = flow.State()
        fm = flow.FlowMaster(None, s)
        req = tutils.treq()

        fm.handle_clientconnect(req.client_conn)

        f = fm.handle_request(req)
        assert len(s.flow_list) == 1

        resp = tutils.tresp(req)
        fm.handle_response(resp)
        assert len(s.flow_list) == 1

        rx = tutils.tresp()
        assert not fm.handle_response(rx)
        
        dc = proxy.ClientDisconnect(req.client_conn)
        fm.handle_clientdisconnect(dc)

        err = proxy.Error(f.request, "msg")
        fm.handle_error(err)

    def test_server_playback(self):
        s = flow.State()

        f = tutils.tflow()
        f.response = tutils.tresp(f.request)
        pb = [f]

        fm = flow.FlowMaster(None, s)
        assert not fm.do_server_playback(tutils.tflow())

        fm.start_server_playback(pb, False, [])
        assert fm.do_server_playback(tutils.tflow())

        fm.start_server_playback(pb, False, [])
        r = tutils.tflow()
        r.request.content = "gibble"
        assert not fm.do_server_playback(r)

    def test_client_playback(self):
        s = flow.State()
        fm = flow.FlowMaster(None, s)
        pb = [tutils.tflow_full()]
        fm.start_client_playback(pb)

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
        f = fm.handle_response(tf.response)
        assert fm.stickycookie_state.jar
        assert not "cookie" in tf.request.headers
        fm.handle_request(tf.request)
        assert tf.request.headers["cookie"] == ["foo=bar"]





tests = [
    uStickyCookieState(),
    uServerPlaybackState(),
    uClientPlaybackState(),
    uFlow(),
    uState(),
    uSerialize(),
    uFlowMaster()
]
