import base64
import pytest

from mitmproxy import exceptions
from mitmproxy.test import taddons
from mitmproxy.test import tflow
from mitmproxy.addons import upstream_auth


def test_configure():
    up = upstream_auth.UpstreamAuth()
    with taddons.context(up) as tctx:
        tctx.configure(up, upstream_auth="test:test")
        assert up.auth == b"Basic" + b" " + base64.b64encode(b"test:test")

        tctx.configure(up, upstream_auth="test:")
        assert up.auth == b"Basic" + b" " + base64.b64encode(b"test:")

        tctx.configure(up, upstream_auth=None)
        assert not up.auth

        with pytest.raises(exceptions.OptionsError):
            tctx.configure(up, upstream_auth="")
        with pytest.raises(exceptions.OptionsError):
            tctx.configure(up, upstream_auth=":")
        with pytest.raises(exceptions.OptionsError):
            tctx.configure(up, upstream_auth=":test")


def test_simple():
    up = upstream_auth.UpstreamAuth()
    with taddons.context(up) as tctx:
        tctx.configure(up, upstream_auth="foo:bar")

        f = tflow.tflow()
        f.mode = "upstream"
        up.requestheaders(f)
        assert "proxy-authorization" in f.request.headers

        f = tflow.tflow()
        up.requestheaders(f)
        assert "proxy-authorization" not in f.request.headers

        tctx.configure(up, mode="reverse")
        f = tflow.tflow()
        f.mode = "transparent"
        up.requestheaders(f)
        assert "proxy-authorization" in f.request.headers

        f = tflow.tflow()
        f.mode = "upstream"
        up.http_connect(f)
        assert "proxy-authorization" in f.request.headers
