from mitmproxy.addons import intercept
from mitmproxy import options
from mitmproxy import exceptions
from mitmproxy.test import taddons
from mitmproxy.test import tutils


class Options(options.Options):
    def __init__(self, *, intercept=None, **kwargs):
        self.intercept = intercept
        super().__init__(**kwargs)


def test_simple():
    r = intercept.Intercept()
    with taddons.context(options=Options()) as tctx:
        assert not r.filt
        tctx.configure(r, intercept="~q")
        assert r.filt
        tutils.raises(
            exceptions.OptionsError,
            tctx.configure,
            r,
            intercept="~~"
        )
