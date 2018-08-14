import typing

import mitmproxy.command  # noqa
from mitmproxy.language.parser import ParsedCommand, ParsedEntity


async def execute_parsed_line(line: ParsedEntity):
    if isinstance(line, ParsedCommand):
        return await traverse_entity(line.command, line.args)
    else:
        return line


async def traverse_entity(command: typing.Optional["mitmproxy.command.Command"],
                          args: typing.List[ParsedEntity]):
    for i, arg in enumerate(args):
        if isinstance(arg, ParsedCommand):
            args[i] = await traverse_entity(arg.command, arg.args)
        elif isinstance(arg, list):
            args[i] = await traverse_entity(command=None, args=arg)

    if command is not None:
        if command.asyncf:
            return await command.async_call(args)
        else:
            return command.call(args)
    else:
        return args
