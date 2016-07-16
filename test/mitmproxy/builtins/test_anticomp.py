from .. import tutils, mastertest
from mitmproxy.builtins import anticomp
from mitmproxy.flow import master
from mitmproxy.flow import state
from mitmproxy.flow import options


class TestAntiComp(mastertest.MasterTest):
    def test_simple(self):
        s = state.State()
        m = master.FlowMaster(options.Options(anticomp = True), None, s)
        sa = anticomp.AntiComp()
        m.addons.add(sa)

        f = tutils.tflow(resp=True)
        self.invoke(m, "request", f)

        f = tutils.tflow(resp=True)

        f.request.headers["Accept-Encoding"] = "foobar"
        self.invoke(m, "request", f)
        assert f.request.headers["Accept-Encoding"] == "identity"
