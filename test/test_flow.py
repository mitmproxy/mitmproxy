from cStringIO import StringIO
from libmproxy import console, proxy, filt, flow
import utils
import libpry

class uFlow(libpry.AutoTree):
    def test_run_script(self):
        f = utils.tflow()
        f.response = utils.tresp()
        f.request = f.response.request
        se = f.run_script("scripts/a")
        assert "DEBUG" == se.strip()
        assert f.request.host == "TESTOK"

    def test_run_script_err(self):
        f = utils.tflow()
        f.response = utils.tresp()
        f.request = f.response.request
        libpry.raises("returned error", f.run_script,"scripts/err_return")
        libpry.raises("invalid response", f.run_script,"scripts/err_data")
        libpry.raises("no such file", f.run_script,"nonexistent")
        libpry.raises("permission denied", f.run_script,"scripts/nonexecutable")

    def test_match(self):
        f = utils.tflow()
        f.response = utils.tresp()
        f.request = f.response.request
        assert not f.match(filt.parse("~b test"))

    def test_backup(self):
        f = utils.tflow()
        f.response = utils.tresp()
        f.request = f.response.request
        f.request.content = "foo"
        assert not f.modified()
        f.backup()
        f.request.content = "bar"
        assert f.modified()
        f.revert()
        assert f.request.content == "foo"

    def test_getset_state(self):
        f = utils.tflow()
        f.response = utils.tresp()
        f.request = f.response.request
        state = f.get_state() 
        assert f == flow.Flow.from_state(state)

    def test_kill(self):
        f = utils.tflow()
        f.request = utils.treq()
        f.intercept()
        assert not f.request.acked
        f.kill()
        assert f.request.acked
        f.intercept()
        f.response = utils.tresp()
        f.request = f.response.request
        f.request.ack()
        assert not f.response.acked
        f.kill()
        assert f.response.acked

    def test_accept_intercept(self):
        f = utils.tflow()
        f.request = utils.treq()
        f.intercept()
        assert not f.request.acked
        f.accept_intercept()
        assert f.request.acked
        f.response = utils.tresp()
        f.request = f.response.request
        f.intercept()
        f.request.ack()
        assert not f.response.acked
        f.accept_intercept()
        assert f.response.acked

    def test_serialization(self):
        f = flow.Flow(None)
        f.request = utils.treq()


class uState(libpry.AutoTree):
    def test_backup(self):
        bc = proxy.ClientConnect(("address", 22))
        c = flow.State()
        req = utils.treq()
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

        req = utils.treq(bc)
        f = c.add_request(req)
        assert f
        assert len(c.flow_list) == 1
        assert c.flow_map.get(req)

        newreq = utils.treq()
        assert c.add_request(newreq)
        assert c.flow_map.get(newreq)

        resp = utils.tresp(req)
        assert c.add_response(resp)
        assert len(c.flow_list) == 2
        assert c.flow_map.get(resp.request)

        newresp = utils.tresp()
        assert not c.add_response(newresp)
        assert not c.flow_map.get(newresp.request)

        dc = proxy.ClientDisconnect(bc)
        c.clientdisconnect(dc)
        assert not c.client_connections

    def test_err(self):
        bc = proxy.ClientConnect(("address", 22))
        c = flow.State()
        req = utils.treq()
        f = c.add_request(req)
        e = proxy.Error(f, "message")
        assert c.add_error(e)

        e = proxy.Error(utils.tflow(), "message")
        assert not c.add_error(e)

    def test_view(self):
        c = flow.State()

        req = utils.treq()
        c.clientconnect(req.client_conn)
        assert len(c.view) == 0

        f = c.add_request(req)
        assert len(c.view) == 1

        c.set_limit(filt.parse("~s"))
        assert len(c.view) == 0
        resp = utils.tresp(req)
        c.add_response(resp)
        assert len(c.view) == 1
        c.set_limit(None)
        assert len(c.view) == 1

        req = utils.treq()
        c.clientconnect(req.client_conn)
        c.add_request(req)
        assert len(c.view) == 2
        c.set_limit(filt.parse("~q"))
        assert len(c.view) == 1
        c.set_limit(filt.parse("~s"))
        assert len(c.view) == 1

    def _add_request(self, state):
        req = utils.treq()
        f = state.add_request(req)
        return f

    def _add_response(self, state):
        req = utils.treq()
        f = state.add_request(req)
        resp = utils.tresp(req)
        state.add_response(resp)

    def _add_error(self, state):
        req = utils.treq()
        f = state.add_request(req)
        f.error = proxy.Error(f, "msg")

    def test_kill_flow(self):
        c = flow.State()
        req = utils.treq()
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
        f = utils.tflow()
        w = flow.FlowWriter(sio)
        w.add(f)

        sio.seek(0)
        r = flow.FlowReader(sio)
        l = list(r.stream())
        assert len(l) == 1
        assert l[0] == f


class uFlowMaster(libpry.AutoTree):
    def test_one(self):
        s = flow.State()
        f = flow.FlowMaster(None, s)
        req = utils.treq()

        f.handle_request(req)
        assert len(s.flow_list) == 1

        resp = utils.tresp(req)
        f.handle_response(resp)
        assert len(s.flow_list) == 1
        


tests = [
    uFlow(),
    uState(),
    uSerialize(),
    uFlowMaster()

]
