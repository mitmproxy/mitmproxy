import pytest

import mitmproxy.types
from mitmproxy import command
from mitmproxy import ctx
from mitmproxy.test.tflow import tflow
from mitmproxy.tools.console import defaultkeys
from mitmproxy.tools.console import keymap
from mitmproxy.tools.console import master


@pytest.mark.asyncio
async def test_commands_exist():
    command_manager = command.CommandManager(ctx)

    km = keymap.Keymap(None)
    defaultkeys.map(km)
    assert km.bindings
    m = master.ConsoleMaster(None)
    await m.load_flow(tflow())

    for binding in km.bindings:
        try:
            parsed, _ = command_manager.parse_partial(binding.command.strip())

            cmd = parsed[0].value
            args = [
                a.value for a in parsed[1:]
                if a.type != mitmproxy.types.Space
            ]

            assert cmd in m.commands.commands

            cmd_obj = m.commands.commands[cmd]
            cmd_obj.prepare_args(args)
        except Exception as e:
            raise ValueError(f"Invalid binding: {binding.command}") from e
