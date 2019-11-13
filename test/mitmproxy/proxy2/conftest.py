import pytest

from mitmproxy import options
from mitmproxy.addons.proxyserver import Proxyserver
from mitmproxy.proxy2 import context


@pytest.fixture
def tctx():
    opts = options.Options()
    Proxyserver().load(opts)
    return context.Context(
        context.Client(("client", 1234)),
        opts
    )
