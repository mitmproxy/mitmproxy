from .. import tutils, mastertest
from mitmproxy.builtins import anticomp
from mitmproxy.flow import master
from mitmproxy.flow import state
from mitmproxy import options


class TestAntiComp(mastertest.MasterTest):
    def test_simple(self):
        s = state.State()
        o = options.Options(anticomp = True)
        m = master.FlowMaster(o, None, s)
        sa = anticomp.AntiComp()
        m.addons.add(o, sa)

        f = tutils.tflow(resp=True)
        m.request(f)

        f = tutils.tflow(resp=True)

        f.request.headers["Accept-Encoding"] = "foobar"
        m.request(f)
        assert f.request.headers["Accept-Encoding"] == "identity"
