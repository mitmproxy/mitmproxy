import typing
from mitmproxy import command
from mitmproxy import flow
from mitmproxy import exceptions
from mitmproxy.test import tflow
from mitmproxy.test import taddons
import mitmproxy.types
import io
import pytest


class TAddon:
    @command.command("cmd1")
    def cmd1(self, foo: str) -> str:
        """cmd1 help"""
        return "ret " + foo

    @command.command("cmd2")
    def cmd2(self, foo: str) -> str:
        return 99

    @command.command("cmd3")
    def cmd3(self, foo: int) -> int:
        return foo

    @command.command("subcommand")
    def subcommand(self, cmd: mitmproxy.types.Cmd, *args: mitmproxy.types.Arg) -> str:
        return "ok"

    @command.command("empty")
    def empty(self) -> None:
        pass

    @command.command("varargs")
    def varargs(self, one: str, *var: str) -> typing.Sequence[str]:
        return list(var)

    def choices(self) -> typing.Sequence[str]:
        return ["one", "two", "three"]

    @command.argument("arg", type=mitmproxy.types.Choice("choices"))
    def choose(self, arg: str) -> typing.Sequence[str]:
        return ["one", "two", "three"]

    @command.command("path")
    def path(self, arg: mitmproxy.types.Path) -> None:
        pass


class TestCommand:
    def test_varargs(self):
        with taddons.context() as tctx:
            cm = command.CommandManager(tctx.master)
            a = TAddon()
            c = command.Command(cm, "varargs", a.varargs)
            assert c.signature_help() == "varargs str *str -> [str]"
            assert c.call(["one", "two", "three"]) == ["two", "three"]
            with pytest.raises(exceptions.CommandError):
                c.call(["one", "two", 3])

    def test_call(self):
        with taddons.context() as tctx:
            cm = command.CommandManager(tctx.master)
            a = TAddon()
            c = command.Command(cm, "cmd.path", a.cmd1)
            assert c.call(["foo"]) == "ret foo"
            assert c.signature_help() == "cmd.path str -> str"

            c = command.Command(cm, "cmd.two", a.cmd2)
            with pytest.raises(exceptions.CommandError):
                c.call(["foo"])

            c = command.Command(cm, "cmd.three", a.cmd3)
            assert c.call(["1"]) == 1

    def test_parse_partial(self):
        tests = [
            [
                "foo bar",
                [
                    command.ParseResult(value = "foo", type = mitmproxy.types.Cmd),
                    command.ParseResult(value = "bar", type = str)
                ],
            ],
            [
                "foo 'bar",
                [
                    command.ParseResult(value = "foo", type = mitmproxy.types.Cmd),
                    command.ParseResult(value = "'bar", type = str)
                ]
            ],
            ["a", [command.ParseResult(value = "a", type = mitmproxy.types.Cmd)]],
            ["", [command.ParseResult(value = "", type = mitmproxy.types.Cmd)]],
            [
                "cmd3 1",
                [
                    command.ParseResult(value = "cmd3", type = mitmproxy.types.Cmd),
                    command.ParseResult(value = "1", type = int),
                ]
            ],
            [
                "cmd3 ",
                [
                    command.ParseResult(value = "cmd3", type = mitmproxy.types.Cmd),
                    command.ParseResult(value = "", type = int),
                ]
            ],
            [
                "subcommand ",
                [
                    command.ParseResult(value = "subcommand", type = mitmproxy.types.Cmd),
                    command.ParseResult(value = "", type = mitmproxy.types.Cmd),
                ]
            ],
            [
                "subcommand cmd3 ",
                [
                    command.ParseResult(value = "subcommand", type = mitmproxy.types.Cmd),
                    command.ParseResult(value = "cmd3", type = mitmproxy.types.Cmd),
                    command.ParseResult(value = "", type = int),
                ]
            ],
        ]
        with taddons.context() as tctx:
            tctx.master.addons.add(TAddon())
            for s, expected in tests:
                assert tctx.master.commands.parse_partial(s) == expected


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
        with pytest.raises(exceptions.CommandError, match="argument mismatch"):
            c.call("one.two too many args")

        c.add("empty", a.empty)
        c.call("empty")

        fp = io.StringIO()
        c.dump(fp)
        assert fp.getvalue()


def test_typename():
    assert command.typename(str) == "str"
    assert command.typename(typing.Sequence[flow.Flow]) == "[flow]"

    assert command.typename(mitmproxy.types.Data) == "[data]"
    assert command.typename(mitmproxy.types.CutSpec) == "[cut]"

    assert command.typename(flow.Flow) == "flow"
    assert command.typename(typing.Sequence[str]) == "[str]"

    assert command.typename(mitmproxy.types.Choice("foo")) == "choice"
    assert command.typename(mitmproxy.types.Path) == "path"
    assert command.typename(mitmproxy.types.Cmd) == "cmd"


class DummyConsole:
    @command.command("view.resolve")
    def resolve(self, spec: str) -> typing.Sequence[flow.Flow]:
        n = int(spec)
        return [tflow.tflow(resp=True)] * n

    @command.command("cut")
    def cut(self, spec: str) -> mitmproxy.types.Data:
        return [["test"]]


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

        assert command.parsearg(
            tctx.master.commands, "foo", typing.Sequence[str]
        ) == ["foo"]
        assert command.parsearg(
            tctx.master.commands, "foo, bar", typing.Sequence[str]
        ) == ["foo", "bar"]

        a = TAddon()
        tctx.master.commands.add("choices", a.choices)
        assert command.parsearg(
            tctx.master.commands, "one", mitmproxy.types.Choice("choices"),
        ) == "one"
        with pytest.raises(exceptions.CommandError):
            assert command.parsearg(
                tctx.master.commands, "invalid", mitmproxy.types.Choice("choices"),
            )

        assert command.parsearg(
            tctx.master.commands, "foo", mitmproxy.types.Path
        ) == "foo"
        assert command.parsearg(
            tctx.master.commands, "foo", mitmproxy.types.Cmd
        ) == "foo"


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


def test_verify_arg_signature():
    with pytest.raises(exceptions.CommandError):
        command.verify_arg_signature(lambda: None, [1, 2], {})
        print('hello there')
    command.verify_arg_signature(lambda a, b: None, [1, 2], {})
