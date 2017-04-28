import typing
from mitmproxy import command
from mitmproxy import flow
from mitmproxy import master
from mitmproxy import options
from mitmproxy import proxy
from mitmproxy import exceptions
from mitmproxy.test import tflow
from mitmproxy.test import taddons
import pytest


class TAddon:
    def cmd1(self, foo: str) -> str:
        """cmd1 help"""
        return "ret " + foo

    def cmd2(self, foo: str) -> str:
        return 99

    def empty(self) -> None:
        pass


class TestCommand:
    def test_call(self):
        o = options.Options()
        m = master.Master(o, proxy.DummyServer(o))
        cm = command.CommandManager(m)

        a = TAddon()
        c = command.Command(cm, "cmd.path", a.cmd1)
        assert c.call(["foo"]) == "ret foo"
        assert c.signature_help() == "cmd.path str -> str"

        c = command.Command(cm, "cmd.two", a.cmd2)
        with pytest.raises(exceptions.CommandError):
            c.call(["foo"])


def test_simple():
    with taddons.context() as tctx:
        c = command.CommandManager(tctx.master)
        a = TAddon()
        c.add("one.two", a.cmd1)
        assert c.commands["one.two"].help == "cmd1 help"
        assert(c.call("one.two foo") == "ret foo")
        with pytest.raises(exceptions.CommandError, match="Unknown"):
            c.call("nonexistent")
        with pytest.raises(exceptions.CommandError, match="Invalid"):
            c.call("")
        with pytest.raises(exceptions.CommandError, match="Usage"):
            c.call("one.two too many args")

        c.add("empty", a.empty)
        c.call("empty")


def test_typename():
    assert command.typename(str, True) == "str"
    assert command.typename(typing.Sequence[flow.Flow], True) == "[flow]"
    assert command.typename(typing.Sequence[flow.Flow], False) == "flowspec"
    assert command.typename(flow.Flow, False) == "flow"


class DummyConsole:
    def load(self, l):
        l.add_command("view.resolve", self.resolve)

    def resolve(self, spec: str) -> typing.Sequence[flow.Flow]:
        n = int(spec)
        return [tflow.tflow(resp=True)] * n


def test_parsearg():
    with taddons.context() as tctx:
        tctx.master.addons.add(DummyConsole())
        assert command.parsearg(tctx.master.commands, "foo", str) == "foo"

        assert command.parsearg(tctx.master.commands, "1", int) == 1
        with pytest.raises(exceptions.CommandError):
            command.parsearg(tctx.master.commands, "foo", int)

        assert command.parsearg(tctx.master.commands, "true", bool) is True
        assert command.parsearg(tctx.master.commands, "false", bool) is False
        with pytest.raises(exceptions.CommandError):
            command.parsearg(tctx.master.commands, "flobble", bool)

        assert len(command.parsearg(
            tctx.master.commands, "2", typing.Sequence[flow.Flow]
        )) == 2
        assert command.parsearg(tctx.master.commands, "1", flow.Flow)
        with pytest.raises(exceptions.CommandError):
            command.parsearg(tctx.master.commands, "2", flow.Flow)
        with pytest.raises(exceptions.CommandError):
            command.parsearg(tctx.master.commands, "0", flow.Flow)
        with pytest.raises(exceptions.CommandError):
            command.parsearg(tctx.master.commands, "foo", Exception)


class TDec:
    @command.command("cmd1")
    def cmd1(self, foo: str) -> str:
        """cmd1 help"""
        return "ret " + foo

    @command.command("cmd2")
    def cmd2(self, foo: str) -> str:
        return 99

    @command.command("empty")
    def empty(self) -> None:
        pass


def test_decorator():
    with taddons.context() as tctx:
        c = command.CommandManager(tctx.master)
        a = TDec()
        c.collect_commands(a)
        assert "cmd1" in c.commands
        assert c.call("cmd1 bar") == "ret bar"
        assert "empty" in c.commands
        assert c.call("empty") is None

    with taddons.context() as tctx:
        tctx.master.addons.add(a)
        assert tctx.master.commands.call("cmd1 bar") == "ret bar"
