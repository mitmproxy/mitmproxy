from mitmproxy import exceptions
from mitmproxy.addons import core
from mitmproxy.test import taddons
import pytest


def test_simple():
    sa = core.Core()
    with taddons.context() as tctx:
        with pytest.raises(exceptions.OptionsError):
            tctx.configure(sa, body_size_limit = "invalid")
        tctx.configure(sa, body_size_limit = "1m")
        assert tctx.options._processed["body_size_limit"]
