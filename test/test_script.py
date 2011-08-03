import os
from libmproxy import script, flow
import libpry

class uScript(libpry.AutoTree):
    def test_simple(self):
        s = flow.State()
        fm = flow.FlowMaster(None, s)
        ctx = flow.ScriptContext(fm)

        p = script.Script(os.path.join("scripts", "a.py"), ctx)
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

    def test_err(self):
        s = flow.State()
        fm = flow.FlowMaster(None, s)
        ctx = flow.ScriptContext(fm)


        s = script.Script("nonexistent", ctx)
        libpry.raises(
            "no such file",
            s.load
        )

        s = script.Script("scripts", ctx)
        libpry.raises(
            "not a file",
            s.load
        )

        s = script.Script("scripts/syntaxerr.py", ctx)
        libpry.raises(
            script.ScriptError,
            s.load
        )

        s = script.Script("scripts/loaderr.py", ctx)
        libpry.raises(
            script.ScriptError,
            s.load
        )



tests = [
    uScript(),
]

