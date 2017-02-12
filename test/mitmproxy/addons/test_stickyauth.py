from mitmproxy.test import tflow
from mitmproxy.test import taddons
from mitmproxy.test import tutils

from mitmproxy.addons import stickyauth
from mitmproxy import exceptions


def test_configure():
    r = stickyauth.StickyAuth()
    with taddons.context() as tctx:
        tctx.configure(r, stickyauth="~s")
        tutils.raises(
            exceptions.OptionsError,
            tctx.configure,
            r,
            stickyauth="~~"
        )

        tctx.configure(r, stickyauth=None)
        assert not r.flt


def test_simple():
    r = stickyauth.StickyAuth()
    with taddons.context() as tctx:
        tctx.configure(r, stickyauth=".*")
        f = tflow.tflow(resp=True)
        f.request.headers["authorization"] = "foo"
        r.request(f)

        assert "address" in r.hosts

        f = tflow.tflow(resp=True)
        r.request(f)
        assert f.request.headers["authorization"] == "foo"
