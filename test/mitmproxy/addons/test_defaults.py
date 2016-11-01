from mitmproxy import addons


def test_defaults():
    assert addons.default_addons()
