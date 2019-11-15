from mitmproxy.test.tflow import tflow
from mitmproxy.tools.console import defaultkeys
from mitmproxy.tools.console import keymap
from mitmproxy.tools.console import master
from mitmproxy import command
from mitmproxy import ctx
import pytest


@pytest.mark.asyncio
async def test_commands_exist():
    command_manager = command.CommandManager(ctx)

    km = keymap.Keymap(None)
    defaultkeys.map(km)
    assert km.bindings
    m = master.ConsoleMaster(None)
    await m.load_flow(tflow())

    for binding in km.bindings:
        results = command_manager.parse_partial(binding.command)

        cmd = results[0][0].value
        args = [a.value for a in results[0][1:]]

        assert cmd in m.commands.commands

        cmd_obj = m.commands.commands[cmd]
        try:
            cmd_obj.prepare_args(args)
        except Exception as e:

            import pdb
            pdb.set_trace()
            raise ValueError("Invalid command: {}".format(binding.command)) from e
