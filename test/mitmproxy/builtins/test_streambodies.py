from .. import tutils, mastertest
from mitmproxy.flow import state
from mitmproxy.flow import master
from mitmproxy import options

from mitmproxy.builtins import streambodies


class TestStreamBodies(mastertest.MasterTest):
    def test_simple(self):
        s = state.DummyState()
        o = options.Options(stream_large_bodies = 10)
        m = master.FlowMaster(o, None, s)
        sa = streambodies.StreamBodies()
        m.addons.add(sa)

        f = tutils.tflow()
        f.request.content = b""
        f.request.headers["Content-Length"] = "1024"
        assert not f.request.stream
        m.requestheaders(f)
        assert f.request.stream

        f = tutils.tflow(resp=True)
        f.response.content = b""
        f.response.headers["Content-Length"] = "1024"
        assert not f.response.stream
        m.responseheaders(f)
        assert f.response.stream
