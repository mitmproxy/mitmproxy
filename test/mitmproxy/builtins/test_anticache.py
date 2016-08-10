from .. import tutils, mastertest
from mitmproxy.builtins import anticache
from mitmproxy.flow import master
from mitmproxy.flow import state
from mitmproxy import options


class TestAntiCache(mastertest.MasterTest):
    def test_simple(self):
        s = state.State()
        o = options.Options(anticache = True)
        m = master.FlowMaster(o, None, s)
        sa = anticache.AntiCache()
        m.addons.add(o, sa)

        f = tutils.tflow(resp=True)
        m.request(f)

        f = tutils.tflow(resp=True)
        f.request.headers["if-modified-since"] = "test"
        f.request.headers["if-none-match"] = "test"
        m.request(f)
        assert "if-modified-since" not in f.request.headers
        assert "if-none-match" not in f.request.headers
