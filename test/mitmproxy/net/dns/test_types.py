from mitmproxy.net.dns import types


def test_to_str():
    assert types.to_str(types.A) == "A"
    assert types.to_str(0) == "TYPE(0)"


def test_from_str():
    assert types.from_str("A") == types.A
    assert types.from_str("TYPE(0)") == 0
