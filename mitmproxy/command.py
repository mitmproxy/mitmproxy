"""
    This module manages and invokes typed commands.
"""
import inspect
import types
import typing
import textwrap
import functools
import sys

import mitmproxy.types
from mitmproxy import exceptions
from mitmproxy.language import lexer, parser, partial_parser


def verify_arg_signature(f: typing.Callable, args: list, kwargs: dict) -> None:
    sig = inspect.signature(f)
    try:
        sig.bind(*args, **kwargs)
    except TypeError as v:
        raise exceptions.CommandError("command argument mismatch: %s" % v.args[0])


def typename(t: type) -> str:
    """
        Translates a type to an explanatory string.
    """
    if t == inspect._empty:  # type: ignore
        raise exceptions.CommandError("missing type annotation")
    to = mitmproxy.types.CommandTypes.get(t, None)
    if not to:
        raise exceptions.CommandError("unsupported type: %s" % getattr(t, "__name__", t))
    return to.display


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

        self.has_positional = False
        for i in sig.parameters.values():
            # This is the kind for *args parameters
            if i.kind == i.VAR_POSITIONAL:
                self.has_positional = True
        self.paramtypes = [v.annotation for v in sig.parameters.values()]
        if sig.return_annotation == inspect._empty:  # type: ignore
            self.returntype = None
        else:
            self.returntype = sig.return_annotation
        # This fails with a CommandException if types are invalid
        self.signature_help()

    def paramnames(self) -> typing.Sequence[str]:
        v = [typename(i) for i in self.paramtypes]
        if self.has_positional:
            v[-1] = "*" + v[-1]
        return v

    def retname(self) -> str:
        return typename(self.returntype) if self.returntype else ""

    def signature_help(self) -> str:
        params = " ".join(self.paramnames())
        ret = self.retname()
        if ret:
            ret = " -> " + ret
        return "%s %s%s" % (self.path, params, ret)

    def prepare_args(self, args: typing.Sequence[str]) -> typing.List[typing.Any]:
        verify_arg_signature(self.func, list(args), {})

        remainder: typing.Sequence[str] = []
        if self.has_positional:
            remainder = args[len(self.paramtypes) - 1:]
            args = args[:len(self.paramtypes) - 1]

        pargs = []
        for arg, paramtype in zip(args, self.paramtypes):
            pargs.append(parsearg(self.manager, arg, paramtype))
        pargs.extend(remainder)
        return pargs

    def call(self, args: typing.Sequence[str]) -> typing.Any:
        """
            Call the command with a list of arguments. At this point, all
            arguments are strings.
        """
        ret = self.func(*self.prepare_args(args))
        if ret is None and self.returntype is None:
            return
        typ = mitmproxy.types.CommandTypes.get(self.returntype)
        if not typ.is_valid(self.manager, typ, ret):
            raise exceptions.CommandError(
                "%s returned unexpected data - expected %s" % (
                    self.path, typ.display
                )
            )
        return ret


ParseResult = typing.NamedTuple(
    "ParseResult",
    [
        ("value", str),
        ("type", typing.Type),
        ("valid", bool),
    ],
)


class CommandManager(mitmproxy.types._CommandBase):
    def __init__(self, master):
        self.master = master
        self.command_parser = parser.create_parser(self)
        self.partial_parser = partial_parser.create_parser(self)
        self.commands: typing.Dict[str, Command] = {}
        self.oneword_commands: typing.List[str] = []

    def collect_commands(self, addon):
        for i in dir(addon):
            if not i.startswith("__"):
                o = getattr(addon, i)
                try:
                    is_command = hasattr(o, "command_path")
                except Exception:
                    pass  # hasattr may raise if o implements __getattr__.
                else:
                    if is_command:
                        try:
                            self.add(o.command_path, o)
                        except exceptions.CommandError as e:
                            self.master.log.warn(
                                "Could not load command %s: %s" % (o.command_path, e)
                            )

    def add(self, path: str, func: typing.Callable):
        self.commands[path] = Command(self, path, func)
        # Collecting one-word command names for lexer
        if len(path.split(".")) == 1:
            self.oneword_commands.append(path)

    def parse_partial(
        self,
        cmdstr: str
    ) -> typing.Tuple[typing.Sequence[ParseResult], typing.Sequence[str]]:
        """
            Parse a possibly partial command. Returns recursive markup
            structure and whitespaces map.
        """
        lxr = lexer.InteractiveLexer(cmdstr, self.oneword_commands)
        try:
            typer = self.partial_parser.parse(lxr)
        except exceptions.CommandError:
            typer = [("commander_invalid", cmdstr)]
            lxr.whitespace_map = []
        return typer, lxr.whitespace_map

    def call(self, path: str, *args: typing.Sequence[typing.Any]) -> typing.Any:
        """
            Call a command with native arguments. May raise CommandError.
        """
        if path not in self.commands:
            raise exceptions.CommandError("Unknown command: %s" % path)
        return self.commands[path].func(*args)

    def call_strings(self, path: str, args: typing.Sequence[str]) -> typing.Any:
        """
            Call a command using a list of string arguments. May raise CommandError.
        """
        if path not in self.commands:
            raise exceptions.CommandError("Unknown command: %s" % path)
        return self.commands[path].call(args)

    def execute(self, cmdstr: str):
        """
            Execute a command string. May raise CommandError.
        """
        lex = lexer.create_lexer(cmdstr, self.oneword_commands)
        parser_return = self.command_parser.parse(lexer=lex)
        return parser_return

    def dump(self, out=sys.stdout) -> None:
        cmds = list(self.commands.values())
        cmds.sort(key=lambda x: x.signature_help())
        for c in cmds:
            for hl in (c.help or "").splitlines():
                print("# " + hl, file=out)
            print(c.signature_help(), file=out)
            print(file=out)


def parsearg(manager: CommandManager, spec: str, argtype: type) -> typing.Any:
    """
        Convert a string to a argument to the appropriate type.
    """
    t = mitmproxy.types.CommandTypes.get(argtype, None)
    if not t:
        raise exceptions.CommandError("Unsupported argument type: %s" % argtype)
    try:
        return t.parse(manager, argtype, spec)  # type: ignore
    except exceptions.TypeError as e:
        raise exceptions.CommandError from e


def command(path):
    def decorator(function):
        @functools.wraps(function)
        def wrapper(*args, **kwargs):
            verify_arg_signature(function, args, kwargs)
            return function(*args, **kwargs)
        wrapper.__dict__["command_path"] = path
        return wrapper
    return decorator


def argument(name, type):
    """
        Set the type of a command argument at runtime. This is useful for more
        specific types such as mitmproxy.types.Choice, which we cannot annotate
        directly as mypy does not like that.
    """
    def decorator(f: types.FunctionType) -> types.FunctionType:
        assert name in f.__annotations__
        f.__annotations__[name] = type
        return f
    return decorator
