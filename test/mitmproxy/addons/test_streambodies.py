from .. import tutils, mastertest
from mitmproxy import master
from mitmproxy import options
from mitmproxy import proxy

from mitmproxy.addons import streambodies


class TestStreamBodies(mastertest.MasterTest):
    def test_simple(self):
        o = options.Options(stream_large_bodies = 10)
        m = master.Master(o, proxy.DummyServer())
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
