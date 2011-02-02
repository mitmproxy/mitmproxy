from libmproxy import console, proxy, filt, flow
import utils
import libpry

class uFlow(libpry.AutoTree):
    def test_run_script(self):
        f = utils.tflow()
        f.response = utils.tresp()
        f.request = f.response.request
        f, se = f.run_script("scripts/a")
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

    def test_dump(self):
        f = utils.tflow()
        assert f.dump()

    def test_backup(self):
        f = utils.tflow()
        assert not f.modified()
        f.backup()
        assert f.modified()
        f.revert()

    def test_getset_state(self):
        f = utils.tflow()
        state = f.get_state() 
        assert f == flow.Flow.from_state(state)
        f.response = utils.tresp()
        f.request = f.response.request
        state = f.get_state() 
        assert f == flow.Flow.from_state(state)

    def test_simple(self):
        f = utils.tflow()
        assert console.format_flow(f, True)
        assert console.format_flow(f, False)

        f.request = utils.treq()
        assert console.format_flow(f, True)
        assert console.format_flow(f, False)

        f.response = utils.tresp()
        f.response.headers["content-type"] = ["text/html"]
        assert console.format_flow(f, True)
        assert console.format_flow(f, False)
        f.response.code = 404
        assert console.format_flow(f, True)
        assert console.format_flow(f, False)

        assert console.format_flow(f, True)
        assert console.format_flow(f, False)

        f.connection = flow.ReplayConnection()
        assert console.format_flow(f, True)
        assert console.format_flow(f, False)

        f.response = None
        assert console.format_flow(f, True)
        assert console.format_flow(f, False)

        f.error = proxy.Error(200, "test")
        assert console.format_flow(f, True)
        assert console.format_flow(f, False)

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
        bc = proxy.BrowserConnection("address", 22)
        c = flow.State()
        f = flow.Flow(bc)
        c.add_browserconnect(f)

        f.backup()
        c.revert(f)

    def test_flow(self):
        """
            normal flow:

                connect -> request -> response
        """
        bc = proxy.BrowserConnection("address", 22)
        c = flow.State()
        f = flow.Flow(bc)
        c.add_browserconnect(f)
        assert c.lookup(bc)

        req = utils.treq(bc)
        assert c.add_request(req)
        assert len(c.flow_list) == 1
        assert c.lookup(req)

        newreq = utils.treq()
        assert not c.add_request(newreq)
        assert not c.lookup(newreq)

        resp = utils.tresp(req)
        assert c.add_response(resp)
        assert len(c.flow_list) == 1
        assert c.lookup(resp)

        newresp = utils.tresp()
        assert not c.add_response(newresp)
        assert not c.lookup(newresp)

    def test_err(self):
        bc = proxy.BrowserConnection("address", 22)
        c = flow.State()
        f = flow.Flow(bc)
        c.add_browserconnect(f)
        e = proxy.Error(bc, "message")
        assert c.add_error(e)

        e = proxy.Error(proxy.BrowserConnection("address", 22), "message")
        assert not c.add_error(e)

    def test_view(self):
        c = flow.State()

        f = utils.tflow()
        c.add_browserconnect(f)
        assert len(c.view) == 1
        c.set_limit(filt.parse("~q"))
        assert len(c.view) == 0
        c.set_limit(None)

        
        f = utils.tflow()
        req = utils.treq(f.connection)
        c.add_browserconnect(f)
        c.add_request(req)
        assert len(c.view) == 2
        c.set_limit(filt.parse("~q"))
        assert len(c.view) == 1
        c.set_limit(filt.parse("~s"))
        assert len(c.view) == 0

    def _add_request(self, state):
        f = utils.tflow()
        state.add_browserconnect(f)
        q = utils.treq(f.connection)
        state.add_request(q)
        return f

    def _add_response(self, state):
        f = self._add_request(state)
        r = utils.tresp(f.request)
        state.add_response(r)

    def _add_error(self, state):
        f = utils.tflow()
        f.error = proxy.Error(None, "msg")
        state.add_browserconnect(f)
        q = utils.treq(f.connection)
        state.add_request(q)

    def test_kill_flow(self):
        c = flow.State()
        f = utils.tflow()
        c.add_browserconnect(f)
        c.kill_flow(f)
        assert not c.flow_list

    def test_clear(self):
        c = flow.State()
        f = utils.tflow()
        c.add_browserconnect(f)
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

        dump = c.dump_flows()
        c.clear()
        c.load_flows(dump)
        assert isinstance(c.flow_list[0], flow.Flow)

    def test_accept_all(self):
        c = flow.State()
        self._add_request(c)
        self._add_response(c)
        self._add_request(c)
        c.accept_all()



tests = [
    uFlow(),
    uState(),
]
