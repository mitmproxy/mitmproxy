from mitmproxy.test import tflow
from mitmproxy.test import taddons

from mitmproxy.addons import streambodies


def test_simple():
    sa = streambodies.StreamBodies()
    with taddons.context() as tctx:
        tctx.configure(sa, stream_large_bodies = 10)

        f = tflow.tflow()
        f.request.content = b""
        f.request.headers["Content-Length"] = "1024"
        assert not f.request.stream
        sa.requestheaders(f)
        assert f.request.stream

        f = tflow.tflow(resp=True)
        f.response.content = b""
        f.response.headers["Content-Length"] = "1024"
        assert not f.response.stream
        sa.responseheaders(f)
        assert f.response.stream

        f = tflow.tflow(resp=True)
        f.response.headers["content-length"] = "invalid"
        tctx.cycle(sa, f)
