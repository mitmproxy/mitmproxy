import codecs
import os
import glob
import re
import typing

from mitmproxy import exceptions
from mitmproxy import flow
from mitmproxy.utils import emoji, strutils

if typing.TYPE_CHECKING:  # pragma: no cover
    from mitmproxy.command import CommandManager


class Path(str):
    pass


class Cmd(str):
    pass


class CmdArgs(str):
    pass


class Unknown(str):
    pass


class Space(str):
    pass


class CutSpec(typing.Sequence[str]):
    pass


class Data(typing.Sequence[typing.Sequence[typing.Union[str, bytes]]]):
    pass


class Marker(str):
    pass


class Choice:
    def __init__(self, options_command):
        self.options_command = options_command

    def __instancecheck__(self, instance):  # pragma: no cover
        # return false here so that arguments are piped through parsearg,
        # which does extended validation.
        return False


class _BaseType:
    typ: typing.Type = object
    display: str = ""

    def completion(self, manager: "CommandManager", t: typing.Any, s: str) -> typing.Sequence[str]:
        """
            Returns a list of completion strings for a given prefix. The strings
            returned don't necessarily need to be suffixes of the prefix, since
            completers will do prefix filtering themselves..
        """
        raise NotImplementedError

    def parse(self, manager: "CommandManager", typ: typing.Any, s: str) -> typing.Any:
        """
            Parse a string, given the specific type instance (to allow rich type annotations like Choice) and a string.

            Raises exceptions.TypeError if the value is invalid.
        """
        raise NotImplementedError

    def is_valid(self, manager: "CommandManager", typ: typing.Any, val: typing.Any) -> bool:
        """
            Check if data is valid for this type.
        """
        raise NotImplementedError


class _BoolType(_BaseType):
    typ = bool
    display = "bool"

    def completion(self, manager: "CommandManager", t: type, s: str) -> typing.Sequence[str]:
        return ["false", "true"]

    def parse(self, manager: "CommandManager", t: type, s: str) -> bool:
        if s == "true":
            return True
        elif s == "false":
            return False
        else:
            raise exceptions.TypeError(
                "Booleans are 'true' or 'false', got %s" % s
            )

    def is_valid(self, manager: "CommandManager", typ: typing.Any, val: typing.Any) -> bool:
        return val in [True, False]


class _StrType(_BaseType):
    typ = str
    display = "str"

    # https://docs.python.org/3/reference/lexical_analysis.html#string-and-bytes-literals
    escape_sequences = re.compile(r"""
        \\ (
        [\\'"abfnrtv]  # Standard C escape sequence
        | [0-7]{1,3}   # Character with octal value
        | x..          # Character with hex value
        | N{[^}]+}     # Character name in the Unicode database
        | u....        # Character with 16-bit hex value
        | U........    # Character with 32-bit hex value
        )
        """, re.VERBOSE)

    @staticmethod
    def _unescape(match: re.Match) -> str:
        return codecs.decode(match.group(0), "unicode-escape")  # type: ignore

    def completion(self, manager: "CommandManager", t: type, s: str) -> typing.Sequence[str]:
        return []

    def parse(self, manager: "CommandManager", t: type, s: str) -> str:
        try:
            return self.escape_sequences.sub(self._unescape, s)
        except ValueError as e:
            raise exceptions.TypeError(f"Invalid str: {e}") from e

    def is_valid(self, manager: "CommandManager", typ: typing.Any, val: typing.Any) -> bool:
        return isinstance(val, str)


class _BytesType(_BaseType):
    typ = bytes
    display = "bytes"

    def completion(self, manager: "CommandManager", t: type, s: str) -> typing.Sequence[str]:
        return []

    def parse(self, manager: "CommandManager", t: type, s: str) -> bytes:
        try:
            return strutils.escaped_str_to_bytes(s)
        except ValueError as e:
            raise exceptions.TypeError(str(e))

    def is_valid(self, manager: "CommandManager", typ: typing.Any, val: typing.Any) -> bool:
        return isinstance(val, bytes)


class _UnknownType(_BaseType):
    typ = Unknown
    display = "unknown"

    def completion(self, manager: "CommandManager", t: type, s: str) -> typing.Sequence[str]:
        return []

    def parse(self, manager: "CommandManager", t: type, s: str) -> str:
        return s

    def is_valid(self, manager: "CommandManager", typ: typing.Any, val: typing.Any) -> bool:
        return False


class _IntType(_BaseType):
    typ = int
    display = "int"

    def completion(self, manager: "CommandManager", t: type, s: str) -> typing.Sequence[str]:
        return []

    def parse(self, manager: "CommandManager", t: type, s: str) -> int:
        try:
            return int(s)
        except ValueError as e:
            raise exceptions.TypeError(str(e)) from e

    def is_valid(self, manager: "CommandManager", typ: typing.Any, val: typing.Any) -> bool:
        return isinstance(val, int)


class _PathType(_BaseType):
    typ = Path
    display = "path"

    def completion(self, manager: "CommandManager", t: type, start: str) -> typing.Sequence[str]:
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

    def parse(self, manager: "CommandManager", t: type, s: str) -> str:
        return os.path.expanduser(s)

    def is_valid(self, manager: "CommandManager", typ: typing.Any, val: typing.Any) -> bool:
        return isinstance(val, str)


class _CmdType(_BaseType):
    typ = Cmd
    display = "cmd"

    def completion(self, manager: "CommandManager", t: type, s: str) -> typing.Sequence[str]:
        return list(manager.commands.keys())

    def parse(self, manager: "CommandManager", t: type, s: str) -> str:
        if s not in manager.commands:
            raise exceptions.TypeError("Unknown command: %s" % s)
        return s

    def is_valid(self, manager: "CommandManager", typ: typing.Any, val: typing.Any) -> bool:
        return val in manager.commands


class _ArgType(_BaseType):
    typ = CmdArgs
    display = "arg"

    def completion(self, manager: "CommandManager", t: type, s: str) -> typing.Sequence[str]:
        return []

    def parse(self, manager: "CommandManager", t: type, s: str) -> str:
        return s

    def is_valid(self, manager: "CommandManager", typ: typing.Any, val: typing.Any) -> bool:
        return isinstance(val, str)


class _StrSeqType(_BaseType):
    typ = typing.Sequence[str]
    display = "str[]"

    def completion(self, manager: "CommandManager", t: type, s: str) -> typing.Sequence[str]:
        return []

    def parse(self, manager: "CommandManager", t: type, s: str) -> typing.Sequence[str]:
        return [x.strip() for x in s.split(",")]

    def is_valid(self, manager: "CommandManager", typ: typing.Any, val: typing.Any) -> bool:
        if isinstance(val, str) or isinstance(val, bytes):
            return False
        try:
            for v in val:
                if not isinstance(v, str):
                    return False
        except TypeError:
            return False
        return True


class _CutSpecType(_BaseType):
    typ = CutSpec
    display = "cut[]"
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

        "client_conn.peername.port",
        "client_conn.peername.host",
        "client_conn.tls_version",
        "client_conn.sni",
        "client_conn.tls_established",

        "server_conn.address.port",
        "server_conn.address.host",
        "server_conn.ip_address.host",
        "server_conn.tls_version",
        "server_conn.sni",
        "server_conn.tls_established",
    ]

    def completion(self, manager: "CommandManager", t: type, s: str) -> typing.Sequence[str]:
        spec = s.split(",")
        opts = []
        for pref in self.valid_prefixes:
            spec[-1] = pref
            opts.append(",".join(spec))
        return opts

    def parse(self, manager: "CommandManager", t: type, s: str) -> CutSpec:
        parts: typing.Any = s.split(",")
        return parts

    def is_valid(self, manager: "CommandManager", typ: typing.Any, val: typing.Any) -> bool:
        if not isinstance(val, str):
            return False
        parts = [x.strip() for x in val.split(",")]
        for p in parts:
            for pref in self.valid_prefixes:
                if p.startswith(pref):
                    break
            else:
                return False
        return True


class _BaseFlowType(_BaseType):
    viewmarkers = [
        "@all",
        "@focus",
        "@shown",
        "@hidden",
        "@marked",
        "@unmarked",
    ]
    valid_prefixes = viewmarkers + [
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

    def completion(self, manager: "CommandManager", t: type, s: str) -> typing.Sequence[str]:
        return self.valid_prefixes


class _FlowType(_BaseFlowType):
    typ = flow.Flow
    display = "flow"

    def parse(self, manager: "CommandManager", t: type, s: str) -> flow.Flow:
        try:
            flows = manager.execute("view.flows.resolve %s" % (s))
        except exceptions.CommandError as e:
            raise exceptions.TypeError(str(e)) from e
        if len(flows) != 1:
            raise exceptions.TypeError(
                "Command requires one flow, specification matched %s." % len(flows)
            )
        return flows[0]

    def is_valid(self, manager: "CommandManager", typ: typing.Any, val: typing.Any) -> bool:
        return isinstance(val, flow.Flow)


class _FlowsType(_BaseFlowType):
    typ = typing.Sequence[flow.Flow]
    display = "flow[]"

    def parse(self, manager: "CommandManager", t: type, s: str) -> typing.Sequence[flow.Flow]:
        try:
            return manager.execute("view.flows.resolve %s" % (s))
        except exceptions.CommandError as e:
            raise exceptions.TypeError(str(e)) from e

    def is_valid(self, manager: "CommandManager", typ: typing.Any, val: typing.Any) -> bool:
        try:
            for v in val:
                if not isinstance(v, flow.Flow):
                    return False
        except TypeError:
            return False
        return True


class _DataType(_BaseType):
    typ = Data
    display = "data[][]"

    def completion(
        self, manager: "CommandManager", t: type, s: str
    ) -> typing.Sequence[str]:  # pragma: no cover
        raise exceptions.TypeError("data cannot be passed as argument")

    def parse(
        self, manager: "CommandManager", t: type, s: str
    ) -> typing.Any:  # pragma: no cover
        raise exceptions.TypeError("data cannot be passed as argument")

    def is_valid(self, manager: "CommandManager", typ: typing.Any, val: typing.Any) -> bool:
        # FIXME: validate that all rows have equal length, and all columns have equal types
        try:
            for row in val:
                for cell in row:
                    if not (isinstance(cell, str) or isinstance(cell, bytes)):
                        return False
        except TypeError:
            return False
        return True


class _ChoiceType(_BaseType):
    typ = Choice
    display = "choice"

    def completion(self, manager: "CommandManager", t: Choice, s: str) -> typing.Sequence[str]:
        return manager.execute(t.options_command)

    def parse(self, manager: "CommandManager", t: Choice, s: str) -> str:
        opts = manager.execute(t.options_command)
        if s not in opts:
            raise exceptions.TypeError("Invalid choice.")
        return s

    def is_valid(self, manager: "CommandManager", typ: typing.Any, val: typing.Any) -> bool:
        try:
            opts = manager.execute(typ.options_command)
        except exceptions.CommandError:
            return False
        return val in opts


ALL_MARKERS = ['true', 'false'] + list(emoji.emoji)


class _MarkerType(_BaseType):
    typ = Marker
    display = "marker"

    def completion(self, manager: "CommandManager", t: Choice, s: str) -> typing.Sequence[str]:
        return ALL_MARKERS

    def parse(self, manager: "CommandManager", t: Choice, s: str) -> str:
        if s not in ALL_MARKERS:
            raise exceptions.TypeError("Invalid choice.")
        if s == 'true':
            return ":default:"
        elif s == 'false':
            return ""
        return s

    def is_valid(self, manager: "CommandManager", typ: typing.Any, val: str) -> bool:
        return val in ALL_MARKERS


class TypeManager:
    def __init__(self, *types):
        self.typemap = {}
        for t in types:
            self.typemap[t.typ] = t()

    def get(self, t: typing.Optional[typing.Type], default=None) -> typing.Optional[_BaseType]:
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
    _MarkerType,
    _PathType,
    _StrType,
    _StrSeqType,
    _BytesType,
)
