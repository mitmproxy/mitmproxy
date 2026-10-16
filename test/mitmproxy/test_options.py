from mitmproxy import options


def test_simple():
    assert options.Options()


def test_connection_max_per_address():
    opts = options.Options()
    assert opts.connection_max_per_address == 5

    opts = options.Options(connection_max_per_address=10)
    assert opts.connection_max_per_address == 10
