"""
    This module manages and invokes typed commands.
"""
import inspect
import types
import io
import typing
import shlex
import textwrap
import functools
import sys

from mitmproxy import exceptions
import mitmproxy.types


def verify_arg_signature(f: typing.Callable, args: list, kwargs: dict) -> None:
    sig = inspect.signature(f)
    try:
        sig.bind(*args, **kwargs)
    except TypeError as v:
        raise exceptions.CommandError("command argument mismatch: %s" % v.args[0])


def lexer(s):
    # mypy mis-identifies shlex.shlex as abstract
    lex = shlex.shlex(s, posix=True)  # type: ignore
    lex.wordchars += "."
    lex.whitespace_split = True
    lex.commenters = ''
    return lex


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
        self.commands: typing.Dict[str, Command] = {}

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

    def parse_partial(
        self,
        cmdstr: str
    ) -> typing.Tuple[typing.Sequence[ParseResult], typing.Sequence[str]]:
        """
            Parse a possibly partial command. Return a sequence of ParseResults and a sequence of remainder type help items.
        """
        buf = io.StringIO(cmdstr)
        parts: typing.List[str] = []
        lex = lexer(buf)
        while 1:
            remainder = cmdstr[buf.tell():]
            try:
                t = lex.get_token()
            except ValueError:
                parts.append(remainder)
                break
            if not t:
                break
            parts.append(t)
        if not parts:
            parts = [""]
        elif cmdstr.endswith(" "):
            parts.append("")

        parse: typing.List[ParseResult] = []
        params: typing.List[type] = []
        typ: typing.Type = None
        for i in range(len(parts)):
            if i == 0:
                typ = mitmproxy.types.Cmd
                if parts[i] in self.commands:
                    params.extend(self.commands[parts[i]].paramtypes)
            elif params:
                typ = params.pop(0)
                if typ == mitmproxy.types.Cmd and params and params[0] == mitmproxy.types.Arg:
                    if parts[i] in self.commands:
                        params[:] = self.commands[parts[i]].paramtypes
            else:
                typ = mitmproxy.types.Unknown

            to = mitmproxy.types.CommandTypes.get(typ, None)
            valid = False
            if to:
                try:
                    to.parse(self, typ, parts[i])
                except exceptions.TypeError:
                    valid = False
                else:
                    valid = True

            parse.append(
                ParseResult(
                    value=parts[i],
                    type=typ,
                    valid=valid,
                )
            )

        remhelp: typing.List[str] = []
        for x in params:
            remt = mitmproxy.types.CommandTypes.get(x, None)
            remhelp.append(remt.display)

        return parse, remhelp

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
        try:
            parts = list(lexer(cmdstr))
        except ValueError as e:
            raise exceptions.CommandError("Command error: %s" % e)
        if not len(parts) >= 1:
            raise exceptions.CommandError("Invalid command: %s" % cmdstr)
        return self.call_strings(parts[0], parts[1:])

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
