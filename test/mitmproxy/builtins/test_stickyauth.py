from .. import tutils, mastertest
from mitmproxy.builtins import stickyauth
from mitmproxy.flow import master
from mitmproxy.flow import state
from mitmproxy.flow import options


class TestStickyAuth(mastertest.MasterTest):
    def test_simple(self):
        s = state.State()
        m = master.FlowMaster(options.Options(stickyauth = ".*"), None, s)
        sa = stickyauth.StickyAuth()
        m.addons.add(sa)

        f = tutils.tflow(resp=True)
        f.request.headers["authorization"] = "foo"
        self.invoke(m, "request", f)

        assert "address" in sa.hosts

        f = tutils.tflow(resp=True)
        self.invoke(m, "request", f)
        assert f.request.headers["authorization"] == "foo"
