from mitmproxy.net.dns import types


def test_simple():
    assert types.A == 1
    assert types.str(types.A) == "A"
    assert types.str(0) == "TYPE(0)"
