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

        f.focus = True
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


tests = [
    uFlow()
]
