import pytest

from mitmproxy import options
from mitmproxy.proxy2 import context


@pytest.fixture
def tctx():
    return context.Context(
        context.Client(("client", 1234)),
        options.Options()
    )
