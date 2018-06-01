from mitmproxy.test.tflow import tflow
from mitmproxy.tools.console import defaultkeys
from mitmproxy.tools.console import keymap
from mitmproxy.tools.console import master
from mitmproxy.language import lexer

import pytest


@pytest.mark.asyncio
async def test_commands_exist():
    km = keymap.Keymap(None)
    defaultkeys.map(km)
    assert km.bindings
    m = master.ConsoleMaster(None)
    await m.load_flow(tflow())

    for binding in km.bindings:
        cmd, *args = lexer.get_tokens(binding.command)
        assert cmd in m.commands.commands

        cmd_obj = m.commands.commands[cmd]
        try:
            cmd_obj.prepare_args(args)
        except Exception as e:
            raise ValueError("Invalid command: {}".format(binding.command)) from e
