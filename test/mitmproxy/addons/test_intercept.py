import pytest

from mitmproxy.addons import intercept
from mitmproxy import options
from mitmproxy import exceptions
from mitmproxy.test import taddons
from mitmproxy.test import tflow


def test_simple():
    r = intercept.Intercept()
    with taddons.context(options=options.Options()) as tctx:
        assert not r.filt
        tctx.configure(r, intercept="~q")
        assert r.filt
        with pytest.raises(exceptions.OptionsError):
            tctx.configure(r, intercept="~~")
        tctx.configure(r, intercept=None)
        assert not r.filt

        tctx.configure(r, intercept="~s")

        f = tflow.tflow(resp=True)
        tctx.cycle(r, f)
        assert f.intercepted

        f = tflow.tflow(resp=False)
        tctx.cycle(r, f)
        assert not f.intercepted

        f = tflow.tflow(resp=True)
        f.reply._state = "handled"
        r.response(f)
        assert f.intercepted
