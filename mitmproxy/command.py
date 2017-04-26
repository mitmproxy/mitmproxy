import inspect
import typing
import shlex
from mitmproxy.utils import typecheck


class CommandError(Exception):
    pass


def typename(t: type) -> str:
    if t in (str, int, bool):
        return t.__name__
    else:  # pragma: no cover
        raise NotImplementedError


def parsearg(spec: str, argtype: type) -> typing.Any:
    """
        Convert a string to a argument to the appropriate type.
    """
    if argtype == str:
        return spec
    else:
        raise CommandError("Unsupported argument type: %s" % argtype)


class Command:
    def __init__(self, manager, path, func) -> None:
        self.path = path
        self.manager = manager
        self.func = func
        sig = inspect.signature(self.func)
        self.paramtypes = [v.annotation for v in sig.parameters.values()]
        self.returntype = sig.return_annotation

    def signature_help(self) -> str:
        params = " ".join([typename(i) for i in self.paramtypes])
        ret = " -> " + typename(self.returntype) if self.returntype else ""
        return "%s %s%s" % (self.path, params, ret)

    def call(self, args: typing.Sequence[str]):
        """
            Call the command with a set of arguments. At this point, all argumets are strings.
        """
        if len(self.paramtypes) != len(args):
            raise CommandError("SIGNATURE")

        args = [parsearg(args[i], self.paramtypes[i]) for i in range(len(args))]

        with self.manager.master.handlecontext():
            ret = self.func(*args)

        if not typecheck.check_command_return_type(ret, self.returntype):
            raise CommandError("Command returned unexpected data")

        return ret


class CommandManager:
    def __init__(self, master):
        self.master = master
        self.commands = {}

    def add(self, path: str, func: typing.Callable):
        self.commands[path] = Command(self, path, func)

    def call(self, cmdstr: str):
        """
            Call a command using a string. May raise CommandError.
        """
        parts = shlex.split(cmdstr)
        if not len(parts) >= 1:
            raise CommandError("Invalid command: %s" % cmdstr)
        path = parts[0]
        if path not in self.commands:
            raise CommandError("Unknown command: %s" % path)
        return self.commands[path].call(parts[1:])
