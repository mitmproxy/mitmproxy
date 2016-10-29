from mitmproxy.test import tflow
from mitmproxy import proxy
from mitmproxy import master
from mitmproxy.addons import state

from .. import tutils


class TestState:
    def test_duplicate_flow(self):
        s = state.State()
        fm = master.Master(None, proxy.DummyServer())
        fm.addons.add(s)
        f = tflow.tflow(resp=True)
        fm.load_flow(f)
        assert s.flow_count() == 1

        f2 = s.duplicate_flow(f)
        assert f2.response
        assert s.flow_count() == 2
        assert s.index(f2) == 1
