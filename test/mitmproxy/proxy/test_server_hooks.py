from mitmproxy.proxy import server_hooks


def test_noop():
    assert server_hooks
