from mitmproxy.utils import compat


def test_simple():
    assert compat.Server
    assert compat.Client
