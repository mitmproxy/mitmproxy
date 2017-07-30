from mitmproxy.tools.web import master
from mitmproxy import options

from ... import tservers


class TestWebMaster(tservers.MasterTest):
    def mkmaster(self, **opts):
        o = options.Options(**opts)
        return master.WebMaster(o)

    def test_basic(self):
        m = self.mkmaster()
        for i in (1, 2, 3):
            self.dummy_cycle(m, 1, b"")
            assert len(m.view) == i
