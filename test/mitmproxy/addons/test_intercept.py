import pytest

from mitmproxy.addons import intercept
from mitmproxy import exceptions
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
