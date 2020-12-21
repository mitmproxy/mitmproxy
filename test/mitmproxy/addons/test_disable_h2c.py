import io

from mitmproxy.addons import disable_h2c
from mitmproxy.exceptions import Kill
from mitmproxy.net.http import http1
from mitmproxy.test import taddons
from mitmproxy.test import tflow


class TestDisableH2CleartextUpgrade:
    def test_upgrade(self):
        with taddons.context() as tctx:
            a = disable_h2c.DisableH2C()
            tctx.configure(a)

            f = tflow.tflow()
            f.request.headers["upgrade"] = "h2c"
            f.request.headers["connection"] = "foo"
            f.request.headers["http2-settings"] = "bar"

            a.request(f)
            assert "upgrade" not in f.request.headers
            assert "connection" not in f.request.headers
            assert "http2-settings" not in f.request.headers

    def test_prior_knowledge(self):
        with taddons.context() as tctx:
            a = disable_h2c.DisableH2C()
            tctx.configure(a)

            b = io.BytesIO(b"PRI * HTTP/2.0\r\n\r\nSM\r\n\r\n")
            f = tflow.tflow()
            f.request = http1.read_request(b)
            f.intercept()

            a.request(f)
            assert not f.killable
            assert f.reply.value == Kill
