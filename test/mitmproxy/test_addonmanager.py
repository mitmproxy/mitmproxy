from unittest import mock

import pytest

from mitmproxy import addonmanager
from mitmproxy import addons
from mitmproxy import command
from mitmproxy import exceptions
from mitmproxy import hooks
from mitmproxy import master
from mitmproxy import options
from mitmproxy.proxy.layers.http import HttpRequestHook, HttpResponseHook
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


class THalt:
    def running(self):
        raise exceptions.AddonHalt


class AOption:
    def load(self, l):
        l.add_option("custom_option", bool, False, "help")


class AOldAPI:
    def clientconnect(self):
        pass


def test_command():
    with taddons.context() as tctx:
        tctx.master.addons.add(TAddon("test"))
        assert tctx.master.commands.execute("test.command") == "here"


def test_halt():
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


@pytest.mark.asyncio
async def test_lifecycle():
    o = options.Options()
    m = master.Master(o)
    a = addonmanager.AddonManager(m)
    a.add(TAddon("one"))

    with pytest.raises(exceptions.AddonManagerError):
        a.add(TAddon("one"))
    with pytest.raises(exceptions.AddonManagerError):
        a.remove(TAddon("nonexistent"))

    f = tflow.tflow()
    await a.handle_lifecycle(HttpRequestHook(f))

    a._configure_all(o, o.keys())


def test_defaults():
    assert addons.default_addons()


@pytest.mark.asyncio
async def test_loader():
    with taddons.context() as tctx:
        with mock.patch("mitmproxy.ctx.log.warn") as warn:
            l = addonmanager.Loader(tctx.master)
            l.add_option("custom_option", bool, False, "help")
            assert "custom_option" in l.master.options

            # calling this again with the same signature is a no-op.
            l.add_option("custom_option", bool, False, "help")
            assert not warn.called

            # a different signature should emit a warning though.
            l.add_option("custom_option", bool, True, "help")
            assert warn.called

            def cmd(a: str) -> str:
                return "foo"

            l.add_command("test.command", cmd)


@pytest.mark.asyncio
async def test_simple():
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

        a.add(TAddon("one"))

        a.trigger("nonexistent")
        await tctx.master.await_log("AssertionError")

        f = tflow.tflow()
        a.trigger(hooks.RunningHook())
        a.trigger(HttpResponseHook(f))
        await tctx.master.await_log("not callable")

        tctx.master.clear()
        a.get("one").response = addons
        a.trigger(HttpResponseHook(f))
        with pytest.raises(AssertionError):
            await tctx.master.await_log("not callable", timeout=0.01)

        a.remove(a.get("one"))
        assert not a.get("one")

        ta = TAddon("one")
        a.add(ta)
        a.trigger(hooks.RunningHook())
        assert ta.running_called

        assert ta in a


def test_load_option():
    o = options.Options()
    m = master.Master(o)
    a = addonmanager.AddonManager(m)
    a.add(AOption())
    assert "custom_option" in m.options._options


def test_nesting():
    o = options.Options()
    m = master.Master(o)
    a = addonmanager.AddonManager(m)

    a.add(
        TAddon(
            "one",
            addons=[
                TAddon("two"),
                TAddon("three", addons=[TAddon("four")])
            ]
        )
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


@pytest.mark.asyncio
async def test_old_api():
    with taddons.context(loadcore=False) as tctx:
        tctx.master.addons.add(AOldAPI())
        await tctx.master.await_log("clientconnect event has been removed")
