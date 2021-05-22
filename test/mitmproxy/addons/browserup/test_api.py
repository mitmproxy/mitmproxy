import falcon
from falcon import testing
import pytest
from mitmproxy.addons.browserup import har_capture_addon
from mitmproxy.addons.browserup.browserup_addons_manager import BrowserUpAddonsManagerAddOn
import mitmproxy.addons.browserup.browserup_addons_manager
import tempfile
import os
from mitmproxy.test import tflow
from mitmproxy.test import tutils
from mitmproxy.test import taddons
from mitmproxy.utils import data


class TestAPI:
    def flow(self, resp_content=b'message'):
        times = dict(
            timestamp_start=746203200,
            timestamp_end=746203290,
        )

        # Create a dummy flow for testing
        return tflow.tflow(
            req=tutils.treq(method=b'GET', **times),
            resp=tutils.tresp(content=resp_content, **times)
        )


    def client(self):
        a = mitmproxy.addons.browserup.browserup_addons_manager.BrowserUpAddonsManagerAddOn()
        hca = mitmproxy.addons.browserup.browserup_addons_manager.HarCaptureAddOn()
        with taddons.context(a) as ctx:
            ctx.configure(a)
        with taddons.context(hca) as ctx:
            ctx.configure(hca)
        return testing.TestClient(a.get_app())

    # pytest will inject the object returned by the "client" function
    # as an additional parameter.
    def test_healthcheck(self, hc):
        response = self.client().simulate_get('/healthcheck')
        assert response.status == falcon.HTTP_OK

    def test_verify_present(self, hc):
        response = self.client().simulate_post('/verify/present/FindMyName', json={})
        assert response.status == falcon.HTTP_OK

    def test_verify_not_present(self, hc):
        response = self.client().simulate_post('/verify/not_present/DontFindMyName', json={})
        assert response.status == falcon.HTTP_OK

    def test_verify_sla(self, hc):
        response = self.client().simulate_post('/verify/sla/10/LoadsFast', json={})
        assert response.status == falcon.HTTP_OK

    def test_verify_size(self, hc):
        response = self.client().simulate_post('/verify/size/100/NotTooLarge', json={})
        assert response.status == falcon.HTTP_OK

@pytest.fixture()
def path(tmpdir):
    d = tempfile.TemporaryDirectory().name
    return os.path.join(d, 'test.har')

@pytest.fixture()
def hc(path):
    a = har_capture_addon.HarCaptureAddOn()
    with taddons.context(hc) as ctx:
        ctx.configure(a, harcapture=path)
    return a


@pytest.fixture()
def tdata():
    return data.Data(__name__)

