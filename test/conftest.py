import pytest
import OpenSSL
import mitmproxy.net.tcp


requires_alpn = pytest.mark.skipif(
    not mitmproxy.net.tcp.HAS_ALPN,
    reason='requires OpenSSL with ALPN support')


@pytest.fixture()
def disable_alpn(monkeypatch):
    monkeypatch.setattr(mitmproxy.net.tcp, 'HAS_ALPN', False)
    monkeypatch.setattr(OpenSSL.SSL._lib, 'Cryptography_HAS_ALPN', False)
