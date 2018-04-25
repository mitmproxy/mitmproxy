import pytest

from mitmproxy.addons import onboarding
from mitmproxy.test import taddons
from .. import tservers


class TestApp(tservers.HTTPProxyTest):
    def addons(self):
        return [onboarding.Onboarding()]

    @pytest.mark.asyncio
    async def test_basic(self):
        ob = onboarding.Onboarding()
        with taddons.context(ob) as tctx:
            tctx.configure(ob)
            assert self.app("/").status_code == 200

    @pytest.mark.parametrize("ext", ["pem", "p12"])
    @pytest.mark.asyncio
    async def test_cert(self, ext):
        ob = onboarding.Onboarding()
        with taddons.context(ob) as tctx:
            tctx.configure(ob)
            resp = self.app("/cert/%s" % ext)
            assert resp.status_code == 200
            assert resp.content

    @pytest.mark.parametrize("ext", ["pem", "p12"])
    @pytest.mark.asyncio
    async def test_head(self, ext):
        ob = onboarding.Onboarding()
        with taddons.context(ob) as tctx:
            tctx.configure(ob)
            p = self.pathoc()
            with p.connect():
                resp = p.request("head:'http://%s/cert/%s'" % (tctx.options.onboarding_host, ext))
                assert resp.status_code == 200
                assert "Content-Length" in resp.headers
                assert not resp.content
