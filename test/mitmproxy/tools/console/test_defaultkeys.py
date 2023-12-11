import mitmproxy.types
from mitmproxy.test.tflow import tflow


async def test_commands_exist(console):
    await console.load_flow(tflow())

    for binding in console.keymap.bindings:
        try:
            parsed, _ = console.commands.parse_partial(binding.command.strip())

            cmd = parsed[0].value
            args = [a.value for a in parsed[1:] if a.type != mitmproxy.types.Space]

            assert cmd in console.commands.commands

            cmd_obj = console.commands.commands[cmd]
            cmd_obj.prepare_args(args)
        except Exception as e:
            raise ValueError(f"Invalid binding: {binding.command}") from e
