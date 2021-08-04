import inspect
import io
import typing

import pytest

import mitmproxy.types
from mitmproxy import command
from mitmproxy import exceptions
from mitmproxy import flow
from mitmproxy.test import taddons
from mitmproxy.test import tflow


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

    @command.command("cmd4")
    def cmd4(self, a: int, b: str, c: mitmproxy.types.Path) -> str:
        return "ok"

    @command.command("subcommand")
    def subcommand(self, cmd: mitmproxy.types.Cmd, *args: mitmproxy.types.CmdArgs) -> str:
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

    @command.command("flow")
    def flow(self, f: flow.Flow, s: str) -> None:
        pass


class Unsupported:
    pass


class TypeErrAddon:
    @command.command("noret")
    def noret(self):
        pass

    @command.command("invalidret")
    def invalidret(self) -> Unsupported:
        pass

    @command.command("invalidarg")
    def invalidarg(self, u: Unsupported):
        pass


class TestCommand:
    def test_typecheck(self):
        with taddons.context(loadcore=False) as tctx:
            cm = command.CommandManager(tctx.master)
            a = TypeErrAddon()
            command.Command(cm, "noret", a.noret)
            with pytest.raises(exceptions.CommandError):
                command.Command(cm, "invalidret", a.invalidret)
            with pytest.raises(exceptions.CommandError):
                assert command.Command(cm, "invalidarg", a.invalidarg)

    def test_varargs(self):
        with taddons.context() as tctx:
            cm = command.CommandManager(tctx.master)
            a = TAddon()
            c = command.Command(cm, "varargs", a.varargs)
            assert c.signature_help() == "varargs one *var -> str[]"
            assert c.call(["one", "two", "three"]) == ["two", "three"]

    def test_call(self):
        with taddons.context() as tctx:
            cm = command.CommandManager(tctx.master)
            a = TAddon()
            c = command.Command(cm, "cmd.path", a.cmd1)
            assert c.call(["foo"]) == "ret foo"
            assert c.signature_help() == "cmd.path foo -> str"

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
                    command.ParseResult(value="foo", type=mitmproxy.types.Cmd, valid=False),
                    command.ParseResult(value=" ", type=mitmproxy.types.Space, valid=True),
                    command.ParseResult(value="bar", type=mitmproxy.types.Unknown, valid=False)
                ],
                [],
            ],
            [
                "cmd1 'bar",
                [
                    command.ParseResult(value="cmd1", type=mitmproxy.types.Cmd, valid=True),
                    command.ParseResult(value=" ", type=mitmproxy.types.Space, valid=True),
                    command.ParseResult(value="'bar", type=str, valid=True)
                ],
                [],
            ],
            [
                "a",
                [command.ParseResult(value="a", type=mitmproxy.types.Cmd, valid=False)],
                [],
            ],
            [
                "",
                [],
                [
                    command.CommandParameter("", mitmproxy.types.Cmd),
                    command.CommandParameter("", mitmproxy.types.CmdArgs)
                ]
            ],
            [
                "cmd3 1",
                [
                    command.ParseResult(value="cmd3", type=mitmproxy.types.Cmd, valid=True),
                    command.ParseResult(value=" ", type=mitmproxy.types.Space, valid=True),
                    command.ParseResult(value="1", type=int, valid=True),
                ],
                []
            ],
            [
                "cmd3 ",
                [
                    command.ParseResult(value="cmd3", type=mitmproxy.types.Cmd, valid=True),
                    command.ParseResult(value=" ", type=mitmproxy.types.Space, valid=True),
                ],
                [command.CommandParameter('foo', int)]
            ],
            [
                "subcommand ",
                [
                    command.ParseResult(value="subcommand", type=mitmproxy.types.Cmd, valid=True, ),
                    command.ParseResult(value=" ", type=mitmproxy.types.Space, valid=True),
                ],
                [
                    command.CommandParameter('cmd', mitmproxy.types.Cmd),
                    command.CommandParameter('args', mitmproxy.types.CmdArgs, kind=inspect.Parameter.VAR_POSITIONAL),
                ],
            ],
            [
                "varargs one",
                [
                    command.ParseResult(value="varargs", type=mitmproxy.types.Cmd, valid=True),
                    command.ParseResult(value=" ", type=mitmproxy.types.Space, valid=True),
                    command.ParseResult(value="one", type=str, valid=True),
                ],
                [command.CommandParameter('var', str, kind=inspect.Parameter.VAR_POSITIONAL)]
            ],
            [
                "varargs one two three",
                [
                    command.ParseResult(value="varargs", type=mitmproxy.types.Cmd, valid=True),
                    command.ParseResult(value=" ", type=mitmproxy.types.Space, valid=True),
                    command.ParseResult(value="one", type=str, valid=True),
                    command.ParseResult(value=" ", type=mitmproxy.types.Space, valid=True),
                    command.ParseResult(value="two", type=str, valid=True),
                    command.ParseResult(value=" ", type=mitmproxy.types.Space, valid=True),
                    command.ParseResult(value="three", type=str, valid=True),
                ],
                [],
            ],
            [
                "subcommand cmd3 ",
                [
                    command.ParseResult(value="subcommand", type=mitmproxy.types.Cmd, valid=True),
                    command.ParseResult(value=" ", type=mitmproxy.types.Space, valid=True),
                    command.ParseResult(value="cmd3", type=mitmproxy.types.Cmd, valid=True),
                    command.ParseResult(value=" ", type=mitmproxy.types.Space, valid=True),
                ],
                [command.CommandParameter('foo', int)]
            ],
            [
                "cmd4",
                [
                    command.ParseResult(value="cmd4", type=mitmproxy.types.Cmd, valid=True),
                ],
                [
                    command.CommandParameter('a', int),
                    command.CommandParameter('b', str),
                    command.CommandParameter('c', mitmproxy.types.Path),
                ]
            ],
            [
                "cmd4 ",
                [
                    command.ParseResult(value="cmd4", type=mitmproxy.types.Cmd, valid=True),
                    command.ParseResult(value=" ", type=mitmproxy.types.Space, valid=True),
                ],
                [
                    command.CommandParameter('a', int),
                    command.CommandParameter('b', str),
                    command.CommandParameter('c', mitmproxy.types.Path),
                ]
            ],
            [
                "cmd4 1",
                [
                    command.ParseResult(value="cmd4", type=mitmproxy.types.Cmd, valid=True),
                    command.ParseResult(value=" ", type=mitmproxy.types.Space, valid=True),
                    command.ParseResult(value="1", type=int, valid=True),
                ],
                [
                    command.CommandParameter('b', str),
                    command.CommandParameter('c', mitmproxy.types.Path),
                ]
            ],
            [
                "flow",
                [
                    command.ParseResult(value="flow", type=mitmproxy.types.Cmd, valid=True),
                ],
                [
                    command.CommandParameter('f', flow.Flow),
                    command.CommandParameter('s', str),
                ]
            ],
            [
                "flow ",
                [
                    command.ParseResult(value="flow", type=mitmproxy.types.Cmd, valid=True),
                    command.ParseResult(value=" ", type=mitmproxy.types.Space, valid=True),
                ],
                [
                    command.CommandParameter('f', flow.Flow),
                    command.CommandParameter('s', str),
                ]
            ],
            [
                "flow x",
                [
                    command.ParseResult(value="flow", type=mitmproxy.types.Cmd, valid=True),
                    command.ParseResult(value=" ", type=mitmproxy.types.Space, valid=True),
                    command.ParseResult(value="x", type=flow.Flow, valid=False),
                ],
                [
                    command.CommandParameter('s', str),
                ]
            ],
            [
                "flow x ",
                [
                    command.ParseResult(value="flow", type=mitmproxy.types.Cmd, valid=True),
                    command.ParseResult(value=" ", type=mitmproxy.types.Space, valid=True),
                    command.ParseResult(value="x", type=flow.Flow, valid=False),
                    command.ParseResult(value=" ", type=mitmproxy.types.Space, valid=True),
                ],
                [
                    command.CommandParameter('s', str),
                ]
            ],
            [
                "flow \"one two",
                [
                    command.ParseResult(value="flow", type=mitmproxy.types.Cmd, valid=True),
                    command.ParseResult(value=" ", type=mitmproxy.types.Space, valid=True),
                    command.ParseResult(value="\"one two", type=flow.Flow, valid=False),
                ],
                [
                    command.CommandParameter('s', str),
                ]
            ],
            [
                "flow \"three four\"",
                [
                    command.ParseResult(value="flow", type=mitmproxy.types.Cmd, valid=True),
                    command.ParseResult(value=" ", type=mitmproxy.types.Space, valid=True),
                    command.ParseResult(value='"three four"', type=flow.Flow, valid=False),
                ],
                [
                    command.CommandParameter('s', str),
                ]
            ],
            [
                "spaces '    '",
                [
                    command.ParseResult(value="spaces", type=mitmproxy.types.Cmd, valid=False),
                    command.ParseResult(value=" ", type=mitmproxy.types.Space, valid=True),
                    command.ParseResult(value="'    '", type=mitmproxy.types.Unknown, valid=False)
                ],
                [],
            ],
            [
                'spaces2 "    "',
                [
                    command.ParseResult(value="spaces2", type=mitmproxy.types.Cmd, valid=False),
                    command.ParseResult(value=" ", type=mitmproxy.types.Space, valid=True),
                    command.ParseResult(value='"    "', type=mitmproxy.types.Unknown, valid=False)
                ],
                [],
            ],
            [
                '"abc"',
                [
                    command.ParseResult(value='"abc"', type=mitmproxy.types.Cmd, valid=False),
                ],
                [],
            ],
            [
                "'def'",
                [
                    command.ParseResult(value="'def'", type=mitmproxy.types.Cmd, valid=False),
                ],
                [],
            ],
            [
                "cmd10 'a' \"b\" c",
                [
                    command.ParseResult(value="cmd10", type=mitmproxy.types.Cmd, valid=False),
                    command.ParseResult(value=" ", type=mitmproxy.types.Space, valid=True),
                    command.ParseResult(value="'a'", type=mitmproxy.types.Unknown, valid=False),
                    command.ParseResult(value=" ", type=mitmproxy.types.Space, valid=True),
                    command.ParseResult(value='"b"', type=mitmproxy.types.Unknown, valid=False),
                    command.ParseResult(value=" ", type=mitmproxy.types.Space, valid=True),
                    command.ParseResult(value="c", type=mitmproxy.types.Unknown, valid=False),
                ],
                [],
            ],
            [
                "cmd11 'a \"b\" c'",
                [
                    command.ParseResult(value="cmd11", type=mitmproxy.types.Cmd, valid=False),
                    command.ParseResult(value=" ", type=mitmproxy.types.Space, valid=True),
                    command.ParseResult(value="'a \"b\" c'", type=mitmproxy.types.Unknown, valid=False),
                ],
                [],
            ],
            [
                'cmd12 "a \'b\' c"',
                [
                    command.ParseResult(value="cmd12", type=mitmproxy.types.Cmd, valid=False),
                    command.ParseResult(value=" ", type=mitmproxy.types.Space, valid=True),
                    command.ParseResult(value='"a \'b\' c"', type=mitmproxy.types.Unknown, valid=False),
                ],
                [],
            ],
            [
                "    spaces_at_the_begining_are_not_stripped",
                [
                    command.ParseResult(value="    ", type=mitmproxy.types.Space, valid=True),
                    command.ParseResult(value="spaces_at_the_begining_are_not_stripped", type=mitmproxy.types.Cmd,
                                        valid=False),
                ],
                [],
            ],
            [
                "    spaces_at_the_begining_are_not_stripped neither_at_the_end      ",
                [
                    command.ParseResult(value="    ", type=mitmproxy.types.Space, valid=True),
                    command.ParseResult(value="spaces_at_the_begining_are_not_stripped", type=mitmproxy.types.Cmd,
                                        valid=False),
                    command.ParseResult(value=" ", type=mitmproxy.types.Space, valid=True),
                    command.ParseResult(value="neither_at_the_end", type=mitmproxy.types.Unknown, valid=False),
                    command.ParseResult(value="      ", type=mitmproxy.types.Space, valid=True),
                ],
                [],
            ],

        ]

        with taddons.context() as tctx:
            tctx.master.addons.add(TAddon())
            for s, expected, expectedremain in tests:
                current, remain = tctx.master.commands.parse_partial(s)
                assert (s, current, expectedremain) == (s, expected, remain)


def test_simple():
    with taddons.context() as tctx:
        c = command.CommandManager(tctx.master)
        a = TAddon()
        c.add("one.two", a.cmd1)
        assert (c.commands["one.two"].help == "cmd1 help")
        assert (c.execute("one.two foo") == "ret foo")
        assert (c.execute("one.two \"foo\"") == "ret foo")
        assert (c.execute("one.two 'foo bar'") == "ret foo bar")
        assert (c.call("one.two", "foo") == "ret foo")
        with pytest.raises(exceptions.CommandError, match="Unknown"):
            c.execute("nonexistent")
        with pytest.raises(exceptions.CommandError, match="Invalid"):
            c.execute("")
        with pytest.raises(exceptions.CommandError, match="argument mismatch"):
            c.execute("one.two too many args")
        with pytest.raises(exceptions.CommandError, match="Unknown"):
            c.call("nonexistent")
        with pytest.raises(exceptions.CommandError, match="Unknown"):
            c.execute("\\")

        c.add("empty", a.empty)
        c.execute("empty")

        fp = io.StringIO()
        c.dump(fp)
        assert fp.getvalue()


def test_typename():
    assert command.typename(str) == "str"
    assert command.typename(typing.Sequence[flow.Flow]) == "flow[]"

    assert command.typename(mitmproxy.types.Data) == "data[][]"
    assert command.typename(mitmproxy.types.CutSpec) == "cut[]"

    assert command.typename(flow.Flow) == "flow"
    assert command.typename(typing.Sequence[str]) == "str[]"

    assert command.typename(mitmproxy.types.Choice("foo")) == "choice"
    assert command.typename(mitmproxy.types.Path) == "path"
    assert command.typename(mitmproxy.types.Cmd) == "cmd"

    with pytest.raises(exceptions.CommandError, match="missing type annotation"):
        command.typename(inspect._empty)
    with pytest.raises(exceptions.CommandError, match="unsupported type"):
        command.typename(None)


class DummyConsole:
    @command.command("view.flows.resolve")
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
        with pytest.raises(exceptions.CommandError, match="Unsupported"):
            command.parsearg(tctx.master.commands, "foo", type)
        with pytest.raises(exceptions.CommandError):
            command.parsearg(tctx.master.commands, "foo", int)


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


class TAttr:
    def __getattr__(self, item):
        raise OSError


class TAttr2:
    def __getattr__(self, item):
        return TAttr2()


class TCmds(TAttr):
    def __init__(self):
        self.TAttr = TAttr()
        self.TAttr2 = TAttr2()

    @command.command("empty")
    def empty(self) -> None:
        pass


@pytest.mark.asyncio
async def test_collect_commands():
    """
        This tests for errors thrown by getattr() or __getattr__ implementations
        that return an object for .command_name.
    """
    with taddons.context() as tctx:
        c = command.CommandManager(tctx.master)
        a = TCmds()
        c.collect_commands(a)
        assert "empty" in c.commands

        a = TypeErrAddon()
        c.collect_commands(a)
        await tctx.master.await_log("Could not load")


def test_decorator():
    with taddons.context() as tctx:
        c = command.CommandManager(tctx.master)
        a = TDec()
        c.collect_commands(a)
        assert "cmd1" in c.commands
        assert c.execute("cmd1 bar") == "ret bar"
        assert "empty" in c.commands
        assert c.execute("empty") is None

    with taddons.context() as tctx:
        tctx.master.addons.add(a)
        assert tctx.master.commands.execute("cmd1 bar") == "ret bar"


def test_verify_arg_signature():
    with pytest.raises(exceptions.CommandError):
        command.verify_arg_signature(lambda: None, [1, 2], {})
        print('hello there')
    command.verify_arg_signature(lambda a, b: None, [1, 2], {})
