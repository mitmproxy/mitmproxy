import os
from libmproxy import script, flow
import libpry

class uScript(libpry.AutoTree):
    def test_simple(self):
        s = flow.State()
        fm = flow.FlowMaster(None, s)

        p = script.Script(os.path.join("scripts", "a.py"), fm)
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

        s = script.Script("nonexistent", fm)
        libpry.raises(
            script.ScriptError,
            s.load
        )

        s = script.Script(os.path.join("scripts", "syntaxerr.py"), fm)
        libpry.raises(
            script.ScriptError,
            s.load
        )

        s = script.Script(os.path.join("scripts", "loaderr.py"), fm)
        libpry.raises(
            script.ScriptError,
            s.load
        )



tests = [
    uScript(),
]

