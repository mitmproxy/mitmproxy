from libmproxy import script, flow
import tutils
import shlex
import os
import time


class TCounter:
    count = 0

    def __call__(self, *args, **kwargs):
        self.count += 1


class TScriptContext(TCounter):
    def log(self, msg):
        self.__call__()

class TestScript:
    def test_simple(self):
        s = flow.State()
        fm = flow.FlowMaster(None, s)
        ctx = flow.ScriptContext(fm)

        p = script.Script(shlex.split(tutils.test_data.path("scripts/a.py")+" --var 40", posix=(os.name != "nt")), ctx)
        p.load()

        assert "here" in p.ns
        assert p.run("here") == (True, 41)
        assert p.run("here") == (True, 42)

        ret = p.run("errargs")
        assert not ret[0]
        assert len(ret[1]) == 2

        # Check reload
        p.load()
        assert p.run("here") == (True, 41)

    def test_duplicate_flow(self):
        s = flow.State()
        fm = flow.FlowMaster(None, s)
        fm.load_script([tutils.test_data.path("scripts/duplicate_flow.py")])
        r = tutils.treq()
        fm.handle_request(r)
        assert fm.state.flow_count() == 2
        assert not fm.state.view[0].request.is_replay()
        assert fm.state.view[1].request.is_replay()

    def test_err(self):
        s = flow.State()
        fm = flow.FlowMaster(None, s)
        ctx = flow.ScriptContext(fm)


        s = script.Script(["nonexistent"], ctx)
        tutils.raises(
            "no such file",
            s.load
        )

        s = script.Script([tutils.test_data.path("scripts")], ctx)
        tutils.raises(
            "not a file",
            s.load
        )

        s = script.Script([tutils.test_data.path("scripts/syntaxerr.py")], ctx)
        tutils.raises(
            script.ScriptError,
            s.load
        )

        s = script.Script([tutils.test_data.path("scripts/loaderr.py")], ctx)
        tutils.raises(
            script.ScriptError,
            s.load
        )

    def test_concurrent(self):
        s = flow.State()
        fm = flow.FlowMaster(None, s)
        fm.load_script([tutils.test_data.path("scripts/concurrent_decorator.py")])

        reply = TCounter()
        r1, r2 = tutils.treq(), tutils.treq()
        r1.reply, r2.reply = reply, reply
        t_start = time.time()
        fm.handle_request(r1)
        r1.reply()
        fm.handle_request(r2)
        r2.reply()
        assert reply.count < 2
        assert (time.time() - t_start) < 0.09
        time.sleep(0.2)
        assert reply.count == 2

    def test_concurrent2(self):
        ctx = TScriptContext()
        s = script.Script(["scripts/concurrent_decorator.py"], ctx)
        s.load()
        f = tutils.tflow_full()
        f.error = tutils.terr(f.request)
        f.reply = f.request.reply

        print s.run("response", f)
        print s.run("error", f)
        print s.run("clientconnect", f)
        print s.run("clientdisconnect", f)
        print s.run("serverconnect", f)
        time.sleep(0.1)
        assert ctx.count == 5