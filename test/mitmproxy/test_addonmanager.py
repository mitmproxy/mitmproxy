import pytest

from mitmproxy import addons
from mitmproxy import addonmanager
from mitmproxy import exceptions
from mitmproxy import options
from mitmproxy import master
from mitmproxy import proxy
from mitmproxy.test import tflow


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


class THalt:
    def event_custom(self):
        raise exceptions.AddonHalt


class AOption:
    def load(self, l):
        l.add_option("custom_option", bool, False, "help")


class AChain:
    def __init__(self, name, next):
        self.name = name
        self.next = next

    def load(self, l):
        if self.next:
            l.boot_into(self.next)

    def __repr__(self):
        return "<%s>" % self.name


def test_halt():
    o = options.Options()
    m = master.Master(o, proxy.DummyServer(o))
    a = addonmanager.AddonManager(m)
    halt = THalt()
    end = TAddon("end")
    a.add(halt)
    a.add(end)

    a.trigger("custom")
    assert not end.custom_called

    a.remove(halt)
    a.trigger("custom")
    assert end.custom_called


def test_lifecycle():
    o = options.Options()
    m = master.Master(o, proxy.DummyServer(o))
    a = addonmanager.AddonManager(m)
    a.add(TAddon("one"))

    f = tflow.tflow()
    a.handle_lifecycle("request", f)

    a.configure_all(o, o.keys())


def test_defaults():
    assert addons.default_addons()


def test_simple():
    o = options.Options()
    m = master.Master(o, proxy.DummyServer(o))
    a = addonmanager.AddonManager(m)
    with pytest.raises(exceptions.AddonError):
        a.invoke_addon(TAddon("one"), "done")

    assert len(a) == 0
    a.add(TAddon("one"))
    assert a.get("one")
    assert not a.get("two")
    assert len(a) == 1
    a.clear()
    assert len(a) == 0
    assert not a.chain

    a.add(TAddon("one"))
    a.trigger("done")
    with pytest.raises(exceptions.AddonError):
        a.trigger("tick")

    a.remove(a.get("one"))
    assert not a.get("one")

    ta = TAddon("one")
    a.add(ta)
    a.trigger("custom")
    assert ta.custom_called


def test_load_option():
    o = options.Options()
    m = master.Master(o, proxy.DummyServer(o))
    a = addonmanager.AddonManager(m)
    a.add(AOption())
    assert "custom_option" in m.options._options


def test_loadchain():
    o = options.Options()
    m = master.Master(o, proxy.DummyServer(o))
    a = addonmanager.AddonManager(m)

    a.add(AChain("one", None))
    assert a.get("one")
    a.clear()

    a.add(AChain("one", AChain("two", None)))
    assert not a.get("one")
    assert a.get("two")
    a.clear()

    a.add(AChain("one", AChain("two", AChain("three", None))))
    assert not a.get("one")
    assert not a.get("two")
    assert a.get("three")
    a.clear()

    a.add(AChain("one", AChain("two", AChain("three", AChain("four", None)))))
    assert not a.get("one")
    assert not a.get("two")
    assert not a.get("three")
    assert a.get("four")
    a.clear()
