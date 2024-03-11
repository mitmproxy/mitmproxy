import pytest

from mitmproxy import addonmanager
from mitmproxy import addons
from mitmproxy import command
from mitmproxy import exceptions
from mitmproxy import hooks
from mitmproxy import master
from mitmproxy import options
from mitmproxy.addonmanager import Loader
from mitmproxy.proxy.layers.http import HttpRequestHook
from mitmproxy.proxy.layers.http import HttpResponseHook
from mitmproxy.test import taddons
from mitmproxy.test import tflow


class TAddon:
    def __init__(self, name, addons=None):
        self.name = name
        self.response = True
        self.running_called = False
        if addons:
            self.addons = addons

    @command.command("test.command")
    def testcommand(self) -> str:
        return "here"

    def __repr__(self):
        return "Addon(%s)" % self.name

    def done(self):
        pass

    def running(self):
        self.running_called = True


class AsyncTAddon(TAddon):
    async def done(self):
        pass

    async def running(self):
        self.running_called = True


class THalt:
    def running(self):
        raise exceptions.AddonHalt


class AsyncTHalt:
    async def running(self):
        raise exceptions.AddonHalt


class AOption:
    def load(self, loader: Loader):
        loader.add_option("custom_option", bool, False, "help")


class AOldAPI:
    def clientconnect(self):
        pass


def test_command():
    with taddons.context() as tctx:
        tctx.master.addons.add(TAddon("test"))
        assert tctx.master.commands.execute("test.command") == "here"


async def test_halt():
    o = options.Options()
    m = master.Master(o)
    a = addonmanager.AddonManager(m)
    halt = THalt()
    end = TAddon("end")
    a.add(halt)
    a.add(end)

    assert not end.running_called
    a.trigger(hooks.RunningHook())
    assert not end.running_called

    a.remove(halt)
    a.trigger(hooks.RunningHook())
    assert end.running_called


async def test_async_halt():
    o = options.Options()
    m = master.Master(o)
    a = addonmanager.AddonManager(m)
    halt = AsyncTHalt()
    end = AsyncTAddon("end")
    a.add(halt)
    a.add(end)

    assert not end.running_called
    await a.trigger_event(hooks.RunningHook())
    assert not end.running_called

    a.remove(halt)
    await a.trigger_event(hooks.RunningHook())
    assert end.running_called


async def test_lifecycle():
    o = options.Options()
    m = master.Master(o)
    a = addonmanager.AddonManager(m)
    a.add(TAddon("one"))

    assert str(a)

    with pytest.raises(exceptions.AddonManagerError):
        a.add(TAddon("one"))
    with pytest.raises(exceptions.AddonManagerError):
        a.remove(TAddon("nonexistent"))

    f = tflow.tflow()
    await a.handle_lifecycle(HttpRequestHook(f))

    a._configure_all(o.keys())


def test_defaults():
    assert addons.default_addons()


async def test_mixed_async_sync(caplog):
    with taddons.context(loadcore=False) as tctx:
        a = tctx.master.addons

        assert len(a) == 0
        a1 = TAddon("sync")
        a2 = AsyncTAddon("async")
        a.add(a1)
        a.add(a2)

        # test that we can call both sync and async hooks asynchronously
        assert not a1.running_called
        assert not a2.running_called
        await a.trigger_event(hooks.RunningHook())
        assert a1.running_called
        assert a2.running_called

        # test that calling an async hook synchronously fails
        a1.running_called = False
        a2.running_called = False
        a.trigger(hooks.RunningHook())
        assert a1.running_called
        assert "called from sync context" in caplog.text


async def test_loader(caplog):
    with taddons.context() as tctx:
        loader = addonmanager.Loader(tctx.master)
        loader.add_option("custom_option", bool, False, "help")
        assert "custom_option" in loader.master.options

        # calling this again with the same signature is a no-op.
        loader.add_option("custom_option", bool, False, "help")
        assert not caplog.text

        # a different signature should emit a warning though.
        loader.add_option("custom_option", bool, True, "help")
        assert "Over-riding existing option" in caplog.text

        def cmd(a: str) -> str:
            return "foo"

        loader.add_command("test.command", cmd)


async def test_simple(caplog):
    with taddons.context(loadcore=False) as tctx:
        a = tctx.master.addons

        assert len(a) == 0
        a.add(TAddon("one"))
        assert a.get("one")
        assert not a.get("two")
        assert len(a) == 1
        a.clear()
        assert len(a) == 0
        assert not a.chain

    with taddons.context(loadcore=False) as tctx:
        a.add(TAddon("one"))

        a.trigger("nonexistent")
        assert "AssertionError" in caplog.text

        f = tflow.tflow()
        a.trigger(hooks.RunningHook())
        a.trigger(HttpResponseHook(f))
        assert "not callable" in caplog.text
        caplog.clear()

        caplog.clear()
        a.get("one").response = addons
        a.trigger(HttpResponseHook(f))
        assert "not callable" not in caplog.text

        a.remove(a.get("one"))
        assert not a.get("one")

        ta = TAddon("one")
        a.add(ta)
        a.trigger(hooks.RunningHook())
        assert ta.running_called

        assert ta in a


async def test_load_option():
    o = options.Options()
    m = master.Master(o)
    a = addonmanager.AddonManager(m)
    a.add(AOption())
    assert "custom_option" in m.options._options


async def test_nesting():
    o = options.Options()
    m = master.Master(o)
    a = addonmanager.AddonManager(m)

    a.add(
        TAddon("one", addons=[TAddon("two"), TAddon("three", addons=[TAddon("four")])])
    )
    assert len(a.chain) == 1
    assert a.get("one")
    assert a.get("two")
    assert a.get("three")
    assert a.get("four")

    a.trigger(hooks.RunningHook())
    assert a.get("one").running_called
    assert a.get("two").running_called
    assert a.get("three").running_called
    assert a.get("four").running_called

    a.remove(a.get("three"))
    assert not a.get("three")
    assert not a.get("four")


async def test_old_api(caplog):
    with taddons.context(loadcore=False) as tctx:
        tctx.master.addons.add(AOldAPI())
        assert "clientconnect event has been removed" in caplog.text
