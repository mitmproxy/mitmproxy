from mitmproxy import addons
from mitmproxy import controller
from mitmproxy import options
from mitmproxy import proxy


class TAddon:
    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return "Addon(%s)" % self.name


def test_simple():
    o = options.Options()
    m = controller.Master(o, proxy.DummyServer(o))
    a = addons.Addons(m)
    a.add(TAddon("one"))
    assert a.get("one")
    assert not a.get("two")
    a.clear()
    assert not a.chain
