from mitmproxy import command
from mitmproxy import master
from mitmproxy import options
from mitmproxy import proxy
from mitmproxy import exceptions
import pytest


class TAddon:
    def cmd1(self, foo: str) -> str:
        return "ret " + foo


class TestCommand:
    def test_call(self):
        o = options.Options()
        m = master.Master(o, proxy.DummyServer(o))
        cm = command.CommandManager(m)

        a = TAddon()
        c = command.Command(cm, "cmd.path", a.cmd1)
        assert c.call(["foo"]) == "ret foo"
        assert c.signature_help() == "cmd.path str -> str"


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
