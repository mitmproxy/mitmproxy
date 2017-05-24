import os
import pytest
import OpenSSL
import functools
from contextlib import contextmanager

import mitmproxy.net.tcp

pytest_plugins = ('test.full_coverage_plugin',)

requires_alpn = pytest.mark.skipif(
    not mitmproxy.net.tcp.HAS_ALPN,
    reason='requires OpenSSL with ALPN support')

skip_windows = pytest.mark.skipif(
    os.name == "nt",
    reason='Skipping due to Windows'
)

skip_not_windows = pytest.mark.skipif(
    os.name != "nt",
    reason='Skipping due to not Windows'
)

skip_appveyor = pytest.mark.skipif(
    "APPVEYOR" in os.environ,
    reason='Skipping due to Appveyor'
)


@pytest.fixture()
def disable_alpn(monkeypatch):
    monkeypatch.setattr(mitmproxy.net.tcp, 'HAS_ALPN', False)
    monkeypatch.setattr(OpenSSL.SSL._lib, 'Cryptography_HAS_ALPN', False)
