import inspect
import typing
import shlex
import textwrap
import functools

from mitmproxy.utils import typecheck
from mitmproxy import exceptions
from mitmproxy import flow


def typename(t: type, ret: bool) -> str:
    """
        Translates a type to an explanatory string. Ifl ret is True, we're
        looking at a return type, else we're looking at a parameter type.
    """
    if t in (str, int, bool):
        return t.__name__
    elif t == typing.Sequence[flow.Flow]:
        return "[flow]" if ret else "flowspec"
    elif t == flow.Flow:
        return "flow"
    else:  # pragma: no cover
        raise NotImplementedError(t)


class Command:
    def __init__(self, manager, path, func) -> None:
        self.path = path
        self.manager = manager
        self.func = func
        sig = inspect.signature(self.func)
        self.help = None
        if func.__doc__:
            txt = func.__doc__.strip()
            self.help = "\n".join(textwrap.wrap(txt))
        self.paramtypes = [v.annotation for v in sig.parameters.values()]
        self.returntype = sig.return_annotation

    def paramnames(self) -> typing.Sequence[str]:
        return [typename(i, False) for i in self.paramtypes]

    def retname(self) -> str:
        return typename(self.returntype, True) if self.returntype else ""

    def signature_help(self) -> str:
        params = " ".join(self.paramnames())
        ret = self.retname()
        if ret:
            ret = " -> " + ret
        return "%s %s%s" % (self.path, params, ret)

    def call(self, args: typing.Sequence[str]):
        """
            Call the command with a set of arguments. At this point, all argumets are strings.
        """
        if len(self.paramtypes) != len(args):
            raise exceptions.CommandError("Usage: %s" % self.signature_help())

        pargs = []
        for i in range(len(args)):
            pargs.append(parsearg(self.manager, args[i], self.paramtypes[i]))

        with self.manager.master.handlecontext():
            ret = self.func(*pargs)

        if not typecheck.check_command_return_type(ret, self.returntype):
            raise exceptions.CommandError("Command returned unexpected data")

        return ret


class CommandManager:
    def __init__(self, master):
        self.master = master
        self.commands = {}

    def collect_commands(self, addon):
        for i in dir(addon):
            if not i.startswith("__"):
                o = getattr(addon, i)
                if hasattr(o, "command_path"):
                    self.add(o.command_path, o)

    def add(self, path: str, func: typing.Callable):
        self.commands[path] = Command(self, path, func)

    def call_args(self, path, args):
        """
            Call a command using a list of string arguments. May raise CommandError.
        """
        if path not in self.commands:
            raise exceptions.CommandError("Unknown command: %s" % path)
        return self.commands[path].call(args)

    def call(self, cmdstr: str):
        """
            Call a command using a string. May raise CommandError.
        """
        parts = shlex.split(cmdstr)
        if not len(parts) >= 1:
            raise exceptions.CommandError("Invalid command: %s" % cmdstr)
        return self.call_args(parts[0], parts[1:])


def parsearg(manager: CommandManager, spec: str, argtype: type) -> typing.Any:
    """
        Convert a string to a argument to the appropriate type.
    """
    if argtype == str:
        return spec
    elif argtype == typing.Sequence[flow.Flow]:
        return manager.call_args("console.resolve", [spec])
    elif argtype == flow.Flow:
        flows = manager.call_args("console.resolve", [spec])
        if len(flows) != 1:
            raise exceptions.CommandError(
                "Command requires one flow, specification matched %s." % len(flows)
            )
        return flows[0]
    else:
        raise exceptions.CommandError("Unsupported argument type: %s" % argtype)


def command(path):
    def decorator(function):
        @functools.wraps(function)
        def wrapper(*args, **kwargs):
            return function(*args, **kwargs)
        wrapper.__dict__["command_path"] = path
        return wrapper
    return decorator
