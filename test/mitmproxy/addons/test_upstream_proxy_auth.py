import base64

from mitmproxy import exceptions
from mitmproxy.test import taddons
from mitmproxy.test import tflow
from mitmproxy.test import tutils
from mitmproxy.addons import upstream_proxy_auth


def test_configure():
    up = upstream_proxy_auth.UpstreamProxyAuth()
    with taddons.context() as tctx:
        tctx.configure(up, upstream_auth="test:test")
        assert up.auth == b"Basic" + b" " + base64.b64encode(b"test:test")

        tctx.configure(up, upstream_auth="test:")
        assert up.auth == b"Basic" + b" " + base64.b64encode(b"test:")

        tctx.configure(up, upstream_auth=None)
        assert not up.auth

        tutils.raises(
            exceptions.OptionsError,
            tctx.configure,
            up,
            upstream_auth=""
        )
        tutils.raises(
            exceptions.OptionsError,
            tctx.configure,
            up,
            upstream_auth=":"
        )
        tutils.raises(
            exceptions.OptionsError,
            tctx.configure,
            up,
            upstream_auth=":test"
        )


def test_simple():
    up = upstream_proxy_auth.UpstreamProxyAuth()
    with taddons.context() as tctx:
        tctx.configure(up, upstream_auth="foo:bar")

        f = tflow.tflow()
        f.mode = "upstream"
        up.requestheaders(f)
        assert "proxy-authorization" in f.request.headers

        f = tflow.tflow()
        up.requestheaders(f)
        assert "proxy-authorization" not in f.request.headers
