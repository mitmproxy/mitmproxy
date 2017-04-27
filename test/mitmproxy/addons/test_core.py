from mitmproxy.addons import core
from mitmproxy.test import taddons
from mitmproxy import exceptions
import pytest


def test_set():
    sa = core.Core()
    with taddons.context() as tctx:
        assert not tctx.master.options.anticomp
        tctx.command(sa.set, "anticomp")
        assert tctx.master.options.anticomp

        with pytest.raises(exceptions.CommandError):
            tctx.command(sa.set, "nonexistent")
