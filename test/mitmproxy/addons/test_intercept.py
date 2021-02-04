import pytest

from mitmproxy.addons import intercept
from mitmproxy import exceptions
from mitmproxy.proxy import layers
from mitmproxy.test import taddons
from mitmproxy.test import tflow


def test_simple():
    r = intercept.Intercept()
    with taddons.context(r) as tctx:
        assert not r.filt
        tctx.configure(r, intercept="~q")
        assert r.filt
        assert tctx.options.intercept_active
        with pytest.raises(exceptions.OptionsError):
            tctx.configure(r, intercept="~~")
        tctx.configure(r, intercept=None)
        assert not r.filt
        assert not tctx.options.intercept_active

        tctx.configure(r, intercept="~s")

        f = tflow.tflow(resp=True)
        tctx.cycle(r, f)
        assert f.intercepted

        f = tflow.tflow(resp=False)
        tctx.cycle(r, f)
        assert not f.intercepted

        f = tflow.tflow(resp=True)
        r.response(f)
        assert f.intercepted

        tctx.configure(r, intercept_active=False)
        f = tflow.tflow(resp=True)
        tctx.cycle(r, f)
        assert not f.intercepted

        tctx.configure(r, intercept_active=True)
        f = tflow.tflow(resp=True)
        tctx.cycle(r, f)
        assert f.intercepted


def test_tcp():
    r = intercept.Intercept()
    with taddons.context(r) as tctx:
        tctx.configure(r, intercept="~tcp")
        f = tflow.ttcpflow()
        tctx.cycle(r, f)
        assert f.intercepted

        tctx.configure(r, intercept_active=False)
        f = tflow.ttcpflow()
        tctx.cycle(r, f)
        assert not f.intercepted


def test_already_taken():
    r = intercept.Intercept()
    with taddons.context(r) as tctx:
        tctx.configure(r, intercept="~q")

        f = tflow.tflow()
        tctx.invoke(r, layers.http.HttpRequestHook(f))
        assert f.intercepted

        f = tflow.tflow()
        f.reply.take()
        tctx.invoke(r, layers.http.HttpRequestHook(f))
        assert not f.intercepted
