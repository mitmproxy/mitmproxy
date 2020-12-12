from mitmproxy.proxy2 import server_hooks


def test_noop():
    assert server_hooks
