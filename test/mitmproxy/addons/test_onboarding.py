import pytest

from mitmproxy.addons import onboarding
from mitmproxy.test import taddons
from mitmproxy import options
from .. import tservers


class TestApp(tservers.HTTPProxyTest):
    def addons(self):
        return [onboarding.Onboarding()]

    def test_basic(self):
        with taddons.context() as tctx:
            tctx.configure(self.addons()[0])
            assert self.app("/").status_code == 200

    @pytest.mark.parametrize("ext", ["pem", "p12"])
    def test_cert(self, ext):
        with taddons.context() as tctx:
            tctx.configure(self.addons()[0])
            resp = self.app("/cert/%s" % ext)
            assert resp.status_code == 200
            assert resp.content

    @pytest.mark.parametrize("ext", ["pem", "p12"])
    def test_head(self, ext):
        with taddons.context() as tctx:
            tctx.configure(self.addons()[0])
            p = self.pathoc()
            with p.connect():
                resp = p.request("head:'http://%s/cert/%s'" % (options.APP_HOST, ext))
                assert resp.status_code == 200
                assert "Content-Length" in resp.headers
                assert not resp.content
