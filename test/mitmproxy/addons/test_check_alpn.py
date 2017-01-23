from mitmproxy.addons import check_alpn
from mitmproxy.test import taddons
from ...conftest import requires_alpn


class TestCheckALPN:

    @requires_alpn
    def test_check_alpn(self):
        msg = 'ALPN support missing'

        with taddons.context() as tctx:
            a = check_alpn.CheckALPN()
            tctx.configure(a)
            assert not any(msg in m for l, m in tctx.master.event_log)

    def test_check_no_alpn(self, disable_alpn):
        msg = 'ALPN support missing'

        with taddons.context() as tctx:
            a = check_alpn.CheckALPN()
            tctx.configure(a)
            assert any(msg in m for l, m in tctx.master.event_log)
