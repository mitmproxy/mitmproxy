from mitmproxy.net.dns import types


def test_simple():
    assert types.A == 1
    assert types.to_str(types.A) == "A"
    assert types.to_str(0) == "TYPE(0)"
