import os
import glob
import typing

from mitmproxy import exceptions
from mitmproxy import flow


class Path(str):
    pass


class Cmd(str):
    pass


class Arg(str):
    pass


class CutSpec(typing.Sequence[str]):
    pass


class Data(typing.Sequence[typing.Sequence[typing.Union[str, bytes]]]):
    pass


class Choice:
    def __init__(self, options_command):
        self.options_command = options_command

    def __instancecheck__(self, instance):  # pragma: no cover
        # return false here so that arguments are piped through parsearg,
        # which does extended validation.
        return False


# One of the many charming things about mypy is that introducing type
# annotations can cause circular dependencies where there were none before.
# Rather than putting types and the CommandManger in the same file, we introduce
# a stub type with the signature we use.
class _CommandBase:
    commands = {}  # type: typing.MutableMapping[str, typing.Any]

    def call_args(self, path: str, args: typing.Sequence[str]) -> typing.Any:
        raise NotImplementedError

    def call(self, cmd: str) -> typing.Any:
        raise NotImplementedError


class _BaseType:
    typ = object  # type: typing.Type
    display = ""  # type: str

    def completion(
        self, manager: _CommandBase, t: typing.Any, s: str
    ) -> typing.Sequence[str]:  # pragma: no cover
        pass

    def parse(
        self, manager: _CommandBase, t: typing.Any, s: str
    ) -> typing.Any:  # pragma: no cover
        pass


class _BoolType(_BaseType):
    typ = bool
    display = "bool"

    def completion(self, manager: _CommandBase, t: type, s: str) -> typing.Sequence[str]:
        return ["false", "true"]

    def parse(self, manager: _CommandBase, t: type, s: str) -> bool:
        if s == "true":
            return True
        elif s == "false":
            return False
        else:
            raise exceptions.TypeError(
                "Booleans are 'true' or 'false', got %s" % s
            )


class _StrType(_BaseType):
    typ = str
    display = "str"

    def completion(self, manager: _CommandBase, t: type, s: str) -> typing.Sequence[str]:
        return []

    def parse(self, manager: _CommandBase, t: type, s: str) -> str:
        return s


class _IntType(_BaseType):
    typ = int
    display = "int"

    def completion(self, manager: _CommandBase, t: type, s: str) -> typing.Sequence[str]:
        return []

    def parse(self, manager: _CommandBase, t: type, s: str) -> int:
        try:
            return int(s)
        except ValueError as e:
            raise exceptions.TypeError from e


class _PathType(_BaseType):
    typ = Path
    display = "path"

    def completion(self, manager: _CommandBase, t: type, start: str) -> typing.Sequence[str]:
        if not start:
            start = "./"
        path = os.path.expanduser(start)
        ret = []
        if os.path.isdir(path):
            files = glob.glob(os.path.join(path, "*"))
            prefix = start
        else:
            files = glob.glob(path + "*")
            prefix = os.path.dirname(start)
        prefix = prefix or "./"
        for f in files:
            display = os.path.join(prefix, os.path.normpath(os.path.basename(f)))
            if os.path.isdir(f):
                display += "/"
            ret.append(display)
        if not ret:
            ret = [start]
        ret.sort()
        return ret

    def parse(self, manager: _CommandBase, t: type, s: str) -> str:
        return s


class _CmdType(_BaseType):
    typ = Cmd
    display = "cmd"

    def completion(self, manager: _CommandBase, t: type, s: str) -> typing.Sequence[str]:
        return list(manager.commands.keys())

    def parse(self, manager: _CommandBase, t: type, s: str) -> str:
        return s


class _ArgType(_BaseType):
    typ = Arg
    display = "arg"

    def completion(self, manager: _CommandBase, t: type, s: str) -> typing.Sequence[str]:
        return []

    def parse(self, manager: _CommandBase, t: type, s: str) -> str:
        return s


class _StrSeqType(_BaseType):
    typ = typing.Sequence[str]
    display = "[str]"

    def completion(self, manager: _CommandBase, t: type, s: str) -> typing.Sequence[str]:
        return []

    def parse(self, manager: _CommandBase, t: type, s: str) -> typing.Sequence[str]:
        return [x.strip() for x in s.split(",")]


class _CutSpecType(_BaseType):
    typ = CutSpec
    display = "[cut]"
    valid_prefixes = [
        "request.method",
        "request.scheme",
        "request.host",
        "request.http_version",
        "request.port",
        "request.path",
        "request.url",
        "request.text",
        "request.content",
        "request.raw_content",
        "request.timestamp_start",
        "request.timestamp_end",
        "request.header[",

        "response.status_code",
        "response.reason",
        "response.text",
        "response.content",
        "response.timestamp_start",
        "response.timestamp_end",
        "response.raw_content",
        "response.header[",

        "client_conn.address.port",
        "client_conn.address.host",
        "client_conn.tls_version",
        "client_conn.sni",
        "client_conn.ssl_established",

        "server_conn.address.port",
        "server_conn.address.host",
        "server_conn.ip_address.host",
        "server_conn.tls_version",
        "server_conn.sni",
        "server_conn.ssl_established",
    ]

    def completion(self, manager: _CommandBase, t: type, s: str) -> typing.Sequence[str]:
        spec = s.split(",")
        opts = []
        for pref in self.valid_prefixes:
            spec[-1] = pref
            opts.append(",".join(spec))
        return opts

    def parse(self, manager: _CommandBase, t: type, s: str) -> CutSpec:
        parts = s.split(",")  # type: typing.Any
        return parts


class _BaseFlowType(_BaseType):
    valid_prefixes = [
        "@all",
        "@focus",
        "@shown",
        "@hidden",
        "@marked",
        "@unmarked",
        "~q",
        "~s",
        "~a",
        "~hq",
        "~hs",
        "~b",
        "~bq",
        "~bs",
        "~t",
        "~d",
        "~m",
        "~u",
        "~c",
    ]

    def completion(self, manager: _CommandBase, t: type, s: str) -> typing.Sequence[str]:
        return self.valid_prefixes


class _FlowType(_BaseFlowType):
    typ = flow.Flow
    display = "flow"

    def parse(self, manager: _CommandBase, t: type, s: str) -> flow.Flow:
        flows = manager.call_args("view.resolve", [s])
        if len(flows) != 1:
            raise exceptions.TypeError(
                "Command requires one flow, specification matched %s." % len(flows)
            )
        return flows[0]


class _FlowsType(_BaseFlowType):
    typ = typing.Sequence[flow.Flow]
    display = "[flow]"

    def parse(self, manager: _CommandBase, t: type, s: str) -> typing.Sequence[flow.Flow]:
        return manager.call_args("view.resolve", [s])


class _DataType(_BaseType):
    typ = Data
    display = "[data]"

    def completion(
        self, manager: _CommandBase, t: type, s: str
    ) -> typing.Sequence[str]:  # pragma: no cover
        raise exceptions.TypeError("data cannot be passed as argument")

    def parse(
        self, manager: _CommandBase, t: type, s: str
    ) -> typing.Any:  # pragma: no cover
        raise exceptions.TypeError("data cannot be passed as argument")


class _ChoiceType(_BaseType):
    typ = Choice
    display = "choice"

    def completion(self, manager: _CommandBase, t: Choice, s: str) -> typing.Sequence[str]:
        return manager.call(t.options_command)

    def parse(self, manager: _CommandBase, t: Choice, s: str) -> str:
        opts = manager.call(t.options_command)
        if s not in opts:
            raise exceptions.TypeError("Invalid choice.")
        return s


class TypeManager:
    def __init__(self, *types):
        self.typemap = {}
        for t in types:
            self.typemap[t.typ] = t()

    def get(self, t: type, default=None) -> _BaseType:
        if type(t) in self.typemap:
            return self.typemap[type(t)]
        return self.typemap.get(t, default)


CommandTypes = TypeManager(
    _ArgType,
    _BoolType,
    _ChoiceType,
    _CmdType,
    _CutSpecType,
    _DataType,
    _FlowType,
    _FlowsType,
    _IntType,
    _PathType,
    _StrType,
    _StrSeqType,
)
