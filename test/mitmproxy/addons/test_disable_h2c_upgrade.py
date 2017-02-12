from mitmproxy.addons import disable_h2c_upgrade
from mitmproxy.test import tflow


class TestTermLog:
    def test_simple(self):
        a = disable_h2c_upgrade.DisableH2CleartextUpgrade()

        f = tflow.tflow()
        f.request.headers['upgrade'] = 'h2c'
        f.request.headers['connection'] = 'foo'
        f.request.headers['http2-settings'] = 'bar'

        a.request(f)
        assert 'upgrade' not in f.request.headers
        assert 'connection' not in f.request.headers
        assert 'http2-settings' not in f.request.headers
