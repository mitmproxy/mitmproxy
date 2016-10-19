from mitmproxy import addonmanager
from mitmproxy import options
from mitmproxy import master
from mitmproxy import proxy


class TAddon:
    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return "Addon(%s)" % self.name


def test_simple():
    o = options.Options()
    m = master.Master(o, proxy.DummyServer(o))
    a = addonmanager.AddonManager(m)
    a.add(TAddon("one"))
    assert a.get("one")
    assert not a.get("two")
    a.clear()
    assert not a.chain
