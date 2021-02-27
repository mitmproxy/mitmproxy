from mitmproxy import exceptions
from mitmproxy.test import tflow
from mitmproxy.test import taddons
from mitmproxy.addons import streambodies
import pytest


def test_simple():
    sa = streambodies.StreamBodies()
    with taddons.context(sa) as tctx:
        with pytest.raises(exceptions.OptionsError):
            tctx.configure(sa, stream_large_bodies = "invalid")
        tctx.configure(sa, stream_large_bodies = "10")

        # Stream request
        f = tflow.tflow()
        f.request.content = b""
        f.request.headers["Content-Length"] = "1024"
        assert not f.request.stream
        sa.requestheaders(f)
        assert f.request.stream

        # Stream response
        f = tflow.tflow(resp=True)
        f.response.content = b""
        f.response.headers["Content-Length"] = "1024"
        assert not f.response.stream
        sa.responseheaders(f)
        assert f.response.stream

        # Don't stream if content-length header is missing
        f = tflow.tflow(resp=True)
        f.response.content = b""
        assert not f.response.stream
        sa.responseheaders(f)
        assert not f.response.stream

        # Don't stream chunked
        f = tflow.tflow(resp=True)
        f.response.content = b""
        f.response.headers["Transfer-Encoding"] = "chunked"
        assert not f.response.stream
        sa.responseheaders(f)
        assert not f.response.stream

        # Don't stream if a body already exists
        f = tflow.tflow(resp=True)
        f.response.content = b"exists"
        f.response.headers["Content-Length"] = "6"
        assert not f.response.stream
        sa.responseheaders(f)
        assert not f.response.stream

        f = tflow.tflow(resp=True)
        f.response.headers["content-length"] = "invalid"
        tctx.cycle(sa, f)
