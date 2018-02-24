from mitmproxy.test import tflow

from mitmproxy.addons import anticache
from mitmproxy.test import taddons


class TestAntiCache:
    def test_simple(self):
        sa = anticache.AntiCache()
        with taddons.context(sa) as tctx:
            f = tflow.tflow(resp=True)
            f.request.headers["if-modified-since"] = "test"
            f.request.headers["if-none-match"] = "test"

            sa.request(f)
            assert "if-modified-since" in f.request.headers
            assert "if-none-match" in f.request.headers

            tctx.configure(sa, anticache = True)
            sa.request(f)
            assert "if-modified-since" not in f.request.headers
            assert "if-none-match" not in f.request.headers
