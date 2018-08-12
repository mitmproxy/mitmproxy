from mitmproxy.test.tflow import tflow
from mitmproxy.tools.console import defaultkeys
from mitmproxy.tools.console import keymap
from mitmproxy.tools.console import master
from mitmproxy.language import lexer, parser

import pytest


@pytest.mark.asyncio
async def test_commands_exist():
    km = keymap.Keymap(None)
    defaultkeys.map(km)
    assert km.bindings
    m = master.ConsoleMaster(None)
    await m.load_flow(tflow())

    command_parser = parser.create_parser(m.commands)

    for binding in km.bindings:
        lxr = lexer.create_lexer(binding.command, m.commands.oneword_commands)
        try:
            command_parser.parse(lxr, async_exec=True)
        except Exception as e:
            raise ValueError(f"Invalid command: '{binding.command}'") from e
