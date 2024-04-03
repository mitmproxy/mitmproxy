import pytest

from mitmproxy import exceptions
from mitmproxy.addons import intercept
from mitmproxy.test import taddons
from mitmproxy.test import tflow


async def test_simple():
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
        await tctx.cycle(r, f)
        assert f.intercepted

        f = tflow.tflow(resp=False)
        await tctx.cycle(r, f)
        assert not f.intercepted

        f = tflow.tflow(resp=True)
        r.response(f)
        assert f.intercepted

        tctx.configure(r, intercept_active=False)
        f = tflow.tflow(resp=True)
        await tctx.cycle(r, f)
        assert not f.intercepted

        tctx.configure(r, intercept_active=True)
        f = tflow.tflow(resp=True)
        await tctx.cycle(r, f)
        assert f.intercepted


async def test_dns():
    r = intercept.Intercept()
    with taddons.context(r) as tctx:
        tctx.configure(r, intercept="~s ~dns")

        f = tflow.tdnsflow(resp=True)
        await tctx.cycle(r, f)
        assert f.intercepted

        f = tflow.tdnsflow(resp=False)
        await tctx.cycle(r, f)
        assert not f.intercepted

        tctx.configure(r, intercept_active=False)
        f = tflow.tdnsflow(resp=True)
        await tctx.cycle(r, f)
        assert not f.intercepted


async def test_tcp():
    r = intercept.Intercept()
    with taddons.context(r) as tctx:
        tctx.configure(r, intercept="~tcp")
        f = tflow.ttcpflow()
        await tctx.cycle(r, f)
        assert f.intercepted

        tctx.configure(r, intercept_active=False)
        f = tflow.ttcpflow()
        await tctx.cycle(r, f)
        assert not f.intercepted


async def test_udp():
    r = intercept.Intercept()
    with taddons.context(r) as tctx:
        tctx.configure(r, intercept="~udp")
        f = tflow.tudpflow()
        await tctx.cycle(r, f)
        assert f.intercepted

        tctx.configure(r, intercept_active=False)
        f = tflow.tudpflow()
        await tctx.cycle(r, f)
        assert not f.intercepted


async def test_websocket_message():
    r = intercept.Intercept()
    with taddons.context(r) as tctx:
        tctx.configure(r, intercept='~b "hello binary"')
        f = tflow.twebsocketflow()
        await tctx.cycle(r, f)
        assert f.intercepted

        tctx.configure(r, intercept_active=False)
        f = tflow.twebsocketflow()
        await tctx.cycle(r, f)
        assert not f.intercepted
