import os

import pytest
from hypothesis import settings

from mitmproxy import connection, options
from mitmproxy.addons.proxyserver import Proxyserver
from mitmproxy.addons.termlog import TermLog
from mitmproxy.proxy import context


@pytest.fixture
def tctx() -> context.Context:
    opts = options.Options()
    Proxyserver().load(opts)
    TermLog().load(opts)
    return context.Context(
        connection.Client(
            ("client", 1234),
            ("127.0.0.1", 8080),
            1605699329
        ),
        opts
    )


settings.register_profile("fast", max_examples=10)
settings.register_profile("deep", max_examples=100_000, deadline=None)
settings.load_profile(os.getenv("HYPOTHESIS_PROFILE", "fast"))
