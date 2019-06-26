from mitmproxy.test.tflow import tflow
from mitmproxy.tools.console import defaultkeys
from mitmproxy.tools.console import keymap
from mitmproxy.tools.console import master
from mitmproxy import command

import pytest


def master_get_current_view_type():
    return "http1"


@pytest.mark.asyncio
async def test_commands_exist():
    km = keymap.Keymap(None)
    defaultkeys.map(km)
    assert km.bindings
    m = master.ConsoleMaster(None)
    m.get_current_view_type = master_get_current_view_type
    await m.load_flow(tflow())

    for binding in km.bindings:
        cmd, *args = command.lexer(binding.command)
        if not cmd in m.commands.commands:
            print(cmd)
        assert cmd in m.commands.commands

        cmd_obj = m.commands.commands[cmd]
        try:
            cmd_obj.prepare_args(args)
        except Exception as e:
            raise ValueError("Invalid command: {}".format(binding.command)) from e
