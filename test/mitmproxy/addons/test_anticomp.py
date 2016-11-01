from mitmproxy.test import tflow

from .. import mastertest
from mitmproxy.addons import anticomp
from mitmproxy.test import taddons


class TestAntiComp(mastertest.MasterTest):
    def test_simple(self):
        sa = anticomp.AntiComp()
        with taddons.context() as tctx:
            f = tflow.tflow(resp=True)
            sa.request(f)

            tctx.configure(sa, anticomp=True)
            f = tflow.tflow(resp=True)

            f.request.headers["Accept-Encoding"] = "foobar"
            sa.request(f)
            assert f.request.headers["Accept-Encoding"] == "identity"
