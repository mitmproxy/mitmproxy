import pytest

from mitmproxy import addonmanager
from mitmproxy import exceptions
from mitmproxy import options
from mitmproxy import master
from mitmproxy import proxy


class TAddon:
    def __init__(self, name):
        self.name = name
        self.tick = True
        self.custom_called = False

    def __repr__(self):
        return "Addon(%s)" % self.name

    def done(self):
        pass

    def event_custom(self):
        self.custom_called = True


def test_simple():
    o = options.Options()
    m = master.Master(o, proxy.DummyServer(o))
    a = addonmanager.AddonManager(m)
    with pytest.raises(exceptions.AddonError):
        a.invoke_addon(TAddon("one"), "done")

    a.add(TAddon("one"))
    assert a.get("one")
    assert not a.get("two")
    a.clear()
    assert not a.chain

    a.add(TAddon("one"))
    a.trigger("done")
    with pytest.raises(exceptions.AddonError):
        a.trigger("tick")

    ta = TAddon("one")
    a.add(ta)
    a.trigger("custom")
    assert ta.custom_called
