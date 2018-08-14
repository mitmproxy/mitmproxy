import typing
import asyncio

from mitmproxy import command
from mitmproxy.test import taddons
from mitmproxy.language import lexer, parser, traversal

import pytest


class TAddon:
    @command.command("cmd1")
    def cmd1(self, foo: typing.Sequence[str]) -> str:
        return " ".join(foo)

    @command.command("cmd2")
    def cmd2(self, foo: str) -> str:
        return foo

    @command.command("cmd3")
    async def cmd3(self, foo: str) -> str:
        await asyncio.sleep(0.01)
        return foo


@pytest.mark.asyncio
async def test_execute_parsed_line():
    test_commands = ["""join.cmd1 [str.cmd2(abc)
                        str.cmd2(strasync.cmd3("def"))]""",
                     "[1 2 3]", "str.cmd2 abc | strasync.cmd3()"]
    results = ["abc def", ['1', '2', '3'], "abc"]

    with taddons.context() as tctx:
        cm = command.CommandManager(tctx.master)
        a = TAddon()
        cm.add("join.cmd1", a.cmd1)
        cm.add("str.cmd2", a.cmd2)
        cm.add("strasync.cmd3", a.cmd3)

        command_parser = parser.create_parser(cm)
        for cmd, exp_res in zip(test_commands, results):
            lxr = lexer.create_lexer(cmd, cm.oneword_commands)
            parsed = command_parser.parse(lxr, async_exec=True)

            result = await traversal.execute_parsed_line(parsed)
            assert result == exp_res
