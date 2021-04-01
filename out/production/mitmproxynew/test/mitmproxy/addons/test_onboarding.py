import pytest

from mitmproxy.addons import onboarding
from mitmproxy.test import taddons


@pytest.fixture
def client():
    with onboarding.app.test_client() as client:
        yield client


class TestApp:
    def addons(self):
        return [onboarding.Onboarding()]

    @pytest.mark.asyncio
    async def test_basic(self, client):
        ob = onboarding.Onboarding()
        with taddons.context(ob) as tctx:
            tctx.configure(ob)
            assert client.get("/").status_code == 200

    @pytest.mark.parametrize("ext", ["pem", "p12", "cer"])
    @pytest.mark.asyncio
    async def test_cert(self, client, ext, tdata):
        ob = onboarding.Onboarding()
        with taddons.context(ob) as tctx:
            tctx.configure(ob, confdir=tdata.path("mitmproxy/data/confdir"))
            resp = client.get(f"/cert/{ext}")
            assert resp.status_code == 200
            assert resp.data

    @pytest.mark.parametrize("ext", ["pem", "p12", "cer"])
    @pytest.mark.asyncio
    async def test_head(self, client, ext, tdata):
        ob = onboarding.Onboarding()
        with taddons.context(ob) as tctx:
            tctx.configure(ob, confdir=tdata.path("mitmproxy/data/confdir"))
            resp = client.head(f"http://{tctx.options.onboarding_host}/cert/{ext}")
            assert resp.status_code == 200
            assert "Content-Length" in resp.headers
            assert not resp.data
