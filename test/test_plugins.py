import os
from libmproxy import plugins, flow
import libpry

class uPlugin(libpry.AutoTree):
    def test_simple(self):
        s = flow.State()
        fm = flow.FlowMaster(None, s)

        p = plugins.Plugin(os.path.join("plugins", "a.py"), fm)
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

        libpry.raises(IOError, plugins.Plugin, "nonexistent", fm)
        libpry.raises(SyntaxError, plugins.Plugin, os.path.join("plugins", "syntaxerr.py"), fm)



tests = [
    uPlugin(),
]

