from mitmproxy.addons import onboarding
from mitmproxy.test import taddons
from .. import tservers


class TestApp(tservers.HTTPProxyTest):
    def addons(self):
        return [onboarding.Onboarding()]

    def test_basic(self):
        with taddons.context() as tctx:
            tctx.configure(self.addons()[0])
            assert self.app("/").status_code == 200

    def test_cert(self):
        with taddons.context() as tctx:
            tctx.configure(self.addons()[0])
            for ext in ["pem", "p12"]:
                resp = self.app("/cert/%s" % ext)
                assert resp.status_code == 200
                assert resp.content
