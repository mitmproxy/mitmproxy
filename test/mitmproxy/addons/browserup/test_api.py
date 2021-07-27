import falcon
from falcon import testing
import pytest
from mitmproxy.addons.browserup import har_capture_addon
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
        response = self.client().simulate_post('/verify/size/100/NotTooLarge', json={'error_if_no_traffic': True})
        assert response.status == falcon.HTTP_OK

    def test_add_float_counter(self, hc):
        response = self.client().simulate_post('/har/counters', json={'name': 'fooAmount', 'value': 5.0})
        assert response.status == falcon.HTTP_204

    def test_add_integer_counter(self, hc):
        response = self.client().simulate_post('/har/counters', json={'name': 'fooAmount', 'value': 5})
        assert response.status == falcon.HTTP_204

    def test_add_counter_schema_wrong_string_instead_of_number(self, hc):
        response = self.client().simulate_post('/har/counters', json={'name': 3, 'value': 'nope'})
        assert response.status == falcon.HTTP_422

    def test_add_counter_schema_wrong(self, hc):
        response = self.client().simulate_post('/har/counters', json={'name': 3})
        assert response.status == falcon.HTTP_422

    def test_add_error(self, hc):
        response = self.client().simulate_post('/har/errors', json={'name': 'BadError', 'details': 'Woops, super bad'})
        assert response.status == falcon.HTTP_204

    def test_add_error_schema_wrong(self, hc):
        response = self.client().simulate_post('/har/errors', json={'name': 'sdfsd', 'foo': 'Bar'})
        assert response.status == falcon.HTTP_422

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
