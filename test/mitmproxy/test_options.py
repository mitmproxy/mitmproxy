from mitmproxy import options


def test_simple():
    assert options.Options()


def test_tcp_timeout_default():
    opts = options.Options()
    assert opts.tcp_timeout == 600


def test_tcp_timeout_settable():
    opts = options.Options(tcp_timeout=123)
    assert opts.tcp_timeout == 123
