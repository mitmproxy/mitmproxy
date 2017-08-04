import pytest

from mitmproxy.proxy2 import context


@pytest.fixture
def tctx():
    return context.Context(
        context.Client("client"),
        context.Server("server")
    )
