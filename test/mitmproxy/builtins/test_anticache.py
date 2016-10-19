from .. import tutils, mastertest
from mitmproxy.builtins import anticache
from mitmproxy import master
from mitmproxy import options
from mitmproxy import proxy


class TestAntiCache(mastertest.MasterTest):
    def test_simple(self):
        o = options.Options(anticache = True)
        m = master.Master(o, proxy.DummyServer())
        sa = anticache.AntiCache()
        m.addons.add(sa)

        f = tutils.tflow(resp=True)
        m.request(f)

        f = tutils.tflow(resp=True)
        f.request.headers["if-modified-since"] = "test"
        f.request.headers["if-none-match"] = "test"
        m.request(f)
        assert "if-modified-since" not in f.request.headers
        assert "if-none-match" not in f.request.headers
