from libmproxy import script, flow
import tutils

class TestScript:
    def test_simple(self):
        s = flow.State()
        fm = flow.FlowMaster(None, s)
        ctx = flow.ScriptContext(fm)

        p = script.Script(tutils.test_data.path("scripts/a.py"), ctx)
        p.load()
        assert "here" in p.ns
        assert p.run("here") == (True, 1)
        assert p.run("here") == (True, 2)

        ret = p.run("errargs")
        assert not ret[0]
        assert len(ret[1]) == 2

        # Check reload
        p.load()
        assert p.run("here") == (True, 1)

    def test_duplicate_flow(self):
        s = flow.State()
        fm = flow.FlowMaster(None, s)
        fm.load_script(tutils.test_data.path("scripts/duplicate_flow.py"))
        r = tutils.treq()
        fm.handle_request(r)
        assert fm.state.flow_count() == 2
        assert not fm.state.view[0].request.is_replay()
        assert fm.state.view[1].request.is_replay()

    def test_err(self):
        s = flow.State()
        fm = flow.FlowMaster(None, s)
        ctx = flow.ScriptContext(fm)


        s = script.Script("nonexistent", ctx)
        tutils.raises(
            "no such file",
            s.load
        )

        s = script.Script(tutils.test_data.path("scripts"), ctx)
        tutils.raises(
            "not a file",
            s.load
        )

        s = script.Script(tutils.test_data.path("scripts/syntaxerr.py"), ctx)
        tutils.raises(
            script.ScriptError,
            s.load
        )

        s = script.Script(tutils.test_data.path("scripts/loaderr.py"), ctx)
        tutils.raises(
            script.ScriptError,
            s.load
        )

