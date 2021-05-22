from mitmproxy import flow
from mitmproxy.addons import disable_h2c
from mitmproxy.test import taddons, tutils
from mitmproxy.test import tflow


class TestDisableH2CleartextUpgrade:
    def test_upgrade(self):
        with taddons.context() as tctx:
            a = disable_h2c.DisableH2C()
            tctx.configure(a)

            f = tflow.tflow()
            f.request.headers['upgrade'] = 'h2c'
            f.request.headers['connection'] = 'foo'
            f.request.headers['http2-settings'] = 'bar'

            a.request(f)
            assert 'upgrade' not in f.request.headers
            assert 'connection' not in f.request.headers
            assert 'http2-settings' not in f.request.headers

    def test_prior_knowledge(self):
        with taddons.context() as tctx:
            a = disable_h2c.DisableH2C()
            tctx.configure(a)

            f = tflow.tflow()
            f.request = tutils.treq(
                method=b"PRI",
                path=b"*",
                http_version=b"HTTP/2.0",
            )
            f.intercept()

            a.request(f)
            assert not f.killable
            assert f.error.msg == flow.Error.KILLED_MESSAGE
