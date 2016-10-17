from .. import tutils, mastertest
from mitmproxy.builtins import stickyauth
from mitmproxy.flow import master
from mitmproxy import options


class TestStickyAuth(mastertest.MasterTest):
    def test_simple(self):
        o = options.Options(stickyauth = ".*")
        m = master.FlowMaster(o, None)
        sa = stickyauth.StickyAuth()
        m.addons.add(sa)

        f = tutils.tflow(resp=True)
        f.request.headers["authorization"] = "foo"
        m.request(f)

        assert "address" in sa.hosts

        f = tutils.tflow(resp=True)
        m.request(f)
        assert f.request.headers["authorization"] == "foo"
