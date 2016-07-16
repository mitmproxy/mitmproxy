from mitmproxy.web import master
from . import mastertest


class TestWebMaster(mastertest.MasterTest):
    def mkmaster(self, **options):
        o = master.Options(**options)
        return master.WebMaster(None, o)

    def test_basic(self):
        m = self.mkmaster()
        for i in (1, 2, 3):
            self.dummy_cycle(m, 1, b"")
            assert len(m.state.flows) == i
