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
        return "ret " + foo

    def cmd2(self, foo: str) -> str:
        return 99


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
    o = options.Options()
    m = master.Master(o, proxy.DummyServer(o))
    c = command.CommandManager(m)
    a = TAddon()
    c.add("one.two", a.cmd1)
    assert(c.call("one.two foo") == "ret foo")
    with pytest.raises(exceptions.CommandError, match="Unknown"):
        c.call("nonexistent")
    with pytest.raises(exceptions.CommandError, match="Invalid"):
        c.call("")
    with pytest.raises(exceptions.CommandError, match="Usage"):
        c.call("one.two too many args")


def test_typename():
    assert command.typename(str, True) == "str"
    assert command.typename(typing.Sequence[flow.Flow], True) == "[flow]"
    assert command.typename(typing.Sequence[flow.Flow], False) == "flowspec"


class DummyConsole:
    def load(self, l):
        l.add_command("console.resolve", self.resolve)

    def resolve(self, spec: str) -> typing.Sequence[flow.Flow]:
        return [tflow.tflow(resp=True)]


def test_parsearg():
    with taddons.context() as tctx:
        tctx.master.addons.add(DummyConsole())
        assert command.parsearg(tctx.master.commands, "foo", str) == "foo"
        assert len(command.parsearg(
            tctx.master.commands, "~b", typing.Sequence[flow.Flow]
        )) == 1
        with pytest.raises(exceptions.CommandError):
            command.parsearg(tctx.master.commands, "foo", Exception)
