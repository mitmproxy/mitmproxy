import pytest

from mitmproxy.proxy.protocol2 import context


@pytest.fixture
def tctx():
    return context.ClientServerContext(
        context.Client("client"),
        context.Server("server")
    )
